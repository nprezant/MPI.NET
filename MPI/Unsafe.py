"""Runner for Unsafe.pl
Different behavior for different operating systems.

Windows: no change to source
Unix: modifies Unsafe.cs to attempt to match the distrobution and implementation.
"""

from dataclasses import dataclass
import subprocess
import os
import sys
import tempfile

def try_compile(code, cc):
    p = os.path.join(tempfile.gettempdir(), "try_compile.c")
    with open(p, "w") as f:
        f.write(code)
        f.write("int main(void) {}")
    cmd = f"{cc} {p}"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    proc.wait()
    return proc.returncode == 0

def check_lib(lib, func, cc):
    p = os.path.join(tempfile.gettempdir(), "check_lib.c")
    with open(p, "w") as f:
        f.write(
            f"""
            int main(void) {{
                {func}()
            }}
            """
        )
    cmd = f"{cc} {p} -L{lib}"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    proc.wait()
    return proc.returncode == 0

def run_cmd(cmd):
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    proc.wait()
    if proc.returncode != 0:
        print(f"Could not run command. Error: {proc.returncode}. Command: \"{cmd}\"")
        sys.exit(proc.returncode)
    return proc.stdout

@dataclass
class MpiImplementation:
    kind: str
    compileinfo: str
    linkinfo: str
    shared_lib_name: str
    func_prefix: str

if __name__ == "__main__":
    
    # Source code is tailed to windows MSMPI
    if sys.platform.startswith("win32"):
        sys.exit(0)
    
    # Check which kind of MPI we are using
    implementation = None
    if try_compile(
        """
        #include <mpi.h>
        #ifndef MPICH
            #  error Not MPICH
        #endif
        """, "mpicc"):
        print("MPICH-based")
        implementation = MpiImplementation(
            kind="mpich",
            compileinfo="-show",
            linkinfo="-show",
            shared_lib_name="mpich",
            func_prefix="PMPI"
        )

    if try_compile(
        """
        #include <mpi.h>
        #ifndef OPEN_MPI
            #  error Not OpenMPI
        #endif
        """, "mpicc"):
        print("Open MPI")
        implementation = MpiImplementation(
            kind="openmpi",
            compileinfo="--showme:compile",
            linkinfo="--showme:link",
            shared_lib_name="mpi",
            func_prefix="MPI"
        )

    if try_compile(
        """
        #include <mpi.h>
        #ifndef LAM_MPI
            #  error Not LAM/MPI
        #endif
        """, "mpicc"):
        print("LAM/MPI")
        implementation = MpiImplementation(
            kind="lam",
            compileinfo="--showme",
            linkinfo="--showme",
            shared_lib_name="mpi",
            func_prefix="MPI"
        )

    if implementation is None:
        print("Implementation not recognized.")
        sys.exit(1)
    
    # Find the mpi.h header file
    # Note: could use specialized openmpi --showme:incdirs if so inclined
    cmd = r"mpicc -compile-info | grep -o -E -e '-I[^ ]+' | sed 's/^-I//'"
    dirs = [x.decode("utf-8").strip() for x in run_cmd(cmd)]
    
    header = None
    for p in dirs:
        f = os.path.join(p, "mpi.h")
        if os.path.isfile(f):
            header = f
            break
    
    if header is None:
        print("mpi.h header file not found. Locations searched: " + str(dirs), file=sys.stderr)
        sys.exit(1)
    print(f"MPI header: {header}")

    need_cbridge = True
    mpi_libs = ""
    csharp_defines = ""

    if implementation.kind == "mpich":
        # If it's MPICH2-based, make sure that MPICH2 was built as a shared 
        # library (which is not the default). The order of these
        # checks is *very* important, because we rely on the
        # fact that libpmpich depends on libmpich, and that information is
        # only available in the shared library version. So a static pmpich
        # library check will fail while the static mpich check passes; both
        # will pass when a shared MPICH is installed.
        # We do not need the C bridge at all; everything can be done from C#
        need_cbridge = False
        have_libpmpich = True if check_lib("pmpich", "MPI_Init", "mpicc") else False
        have_libmpich = True if check_lib("mpich", "PMPI_Init", "mpicc") else False

        if not have_libpmpich and have_libmpich:
            print("MPICH library is built statically. Please install MPICH built as a shared library by configuring MPICH with the --enable-sharedlibs=??? option")
            sys.exit(1)
    elif implementation.kind == "openmpi":
        # With Open MPI, we need to explicitly determine which libraries
        # the MPI.NET C bridge will need to link against, because libtool
        # has the *extremely annoying* behavior that it completely ignores
        # the compiler wrapper when it is linking.
        ompi_libdirs = run_cmd("mpicc --showme:libdirs")
        ompi_libs = run_cmd("mpicc --showme:libs")
        for dir in ompi_libdirs:
            mpi_libs = f"{mpi_libs} -L{dir}"
        for lib in ompi_libs:
            mpi_libs = f"{mpi_libs} -l{lib}"

    # If we need a C bridge, it' because MPI handles are actually pointers
    if need_cbridge:
        csharp_defines = f"{csharp_defines} -define:MPI_HANDLES_ARE_POINTERS"
    
    # Get size of int, size_t, etc. for Unsafe.pl
    out = run_cmd(r"cc sizes.c -o sizes.out && ./sizes.out | sed -E 's/^.*sizeof\([^\)]+\) = ([0-9]+).*$/\1/'")
    sizes = [x.decode("utf-8").strip() for x in out]
    assert len(sizes) == 4, "Expected 4 sizes output from sizes.c"
    size_int = sizes[0]
    size_long = sizes[1]
    size_longlong = sizes[2]
    size_size_t = sizes[3]
    print("Sizes:", sizes)

    # Run the perl script to modify Unsafe.cs and generate cbridge.c
    cmd = f"perl Unsafe.pl {header} Unsafe.cs CustomUnsafe.cs cbridge.c {' '.join(sizes)}"
    print(cmd)
    run_cmd(cmd)
    os.unlink("Unsafe.cs")
    os.rename("CustomUnsafe.cs", "Unsafe.cs")



