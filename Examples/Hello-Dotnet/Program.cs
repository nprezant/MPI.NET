// See https://aka.ms/new-console-template for more information
using System;
using System.Text;
using MPI;

Console.WriteLine("Hello world");

MPI.Environment.Run(ref args, communicator =>
{
    Console.WriteLine("Hello, from process number "
                             + communicator.Rank + " of "
                             + communicator.Size);
});
Console.WriteLine("done");
