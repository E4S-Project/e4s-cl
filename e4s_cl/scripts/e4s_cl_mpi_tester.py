#!/usr/bin/env python3

import logging
import ctypes
from sys import argv
from pathlib import Path
from argparse import ArgumentParser
from sotools.linker import resolve

DESCRIPTION = """This script will dynamically load an MPI library for the family passed as an argument and run a simple program with it. This serves no purpose by itself and is meant to be traced to list the files an arbitrary MPI library requires to run."""
EPILOG = """Please report any issues to http://github.com/E4S-Project/e4s-cl."""

PARSER = ArgumentParser(
    prog=argv[0],
    description=DESCRIPTION,
    epilog=EPILOG,
)

PARSER.add_argument(
    "family",
    choices=['openmpi', 'mpich'],
    help="The MPI family to search for.",
)

PARSER.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Trace resolving attempts while searching for the library",
)

SONAMES = {
    "openmpi": "libmpi.so.40",
    "mpich": "libmpi.so.12",
}


class MPIhandles:
    pass


def bind_mpich(libpath: Path) -> object:
    logging.debug("Creating bindings using MPICH library '%s'", libpath)
    lib = ctypes.CDLL(libpath)

    MPI = MPIhandles()
    setattr(MPI, "Init", getattr(lib, "MPI_Init"))
    setattr(MPI, "Comm_size", getattr(lib, "MPI_Comm_size"))
    setattr(MPI, "Comm_rank", getattr(lib, "MPI_Comm_rank"))
    setattr(MPI, "Get_processor_name", getattr(lib, "MPI_Get_processor_name"))
    setattr(MPI, "Finalize", getattr(lib, "MPI_Finalize"))
    setattr(MPI, "Barrier", getattr(lib, "MPI_Barrier"))
    setattr(MPI, "Allreduce", getattr(lib, "MPI_Allreduce"))
    setattr(MPI, "COMM_WORLD", ctypes.c_int(0x44000000))
    setattr(MPI, "FLOAT", ctypes.c_int(0x4c00040a))
    setattr(MPI, "SUM", ctypes.c_int(0x58000003))
    setattr(MPI, "MAX_PROCESSOR_NAME", 128)

    return MPI


def bind_ompi(libpath: Path) -> object:
    logging.debug("Creating bindings using OpenMPI library '%s'", libpath)
    lib = ctypes.CDLL(libpath)

    MPI = MPIhandles()
    setattr(MPI, "Init", getattr(lib, "MPI_Init"))
    setattr(MPI, "Comm_size", getattr(lib, "MPI_Comm_size"))
    setattr(MPI, "Comm_rank", getattr(lib, "MPI_Comm_rank"))
    setattr(MPI, "Get_processor_name", getattr(lib, "MPI_Get_processor_name"))
    setattr(MPI, "Finalize", getattr(lib, "MPI_Finalize"))
    setattr(MPI, "Barrier", getattr(lib, "MPI_Barrier"))
    setattr(MPI, "Allreduce", getattr(lib, "MPI_Allreduce"))
    setattr(MPI, "COMM_WORLD", getattr(lib, "ompi_mpi_comm_world"))
    setattr(MPI, "FLOAT", getattr(lib, "ompi_mpi_float"))
    setattr(MPI, "SUM", getattr(lib, "ompi_mpi_op_sum"))
    setattr(MPI, "MAX_PROCESSOR_NAME", 256)

    return MPI


def main():
    args = PARSER.parse_args()

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s",
        )

    # The below line could be expanded to target multiple sonames
    soname = SONAMES.get(args.family)

    library = resolve(soname)
    if library is None:
        logging.error(
            "Failed to locate required library '%s': is the module loaded ?",
            soname)
        exit(1)

    try:
        if args.family == "openmpi":
            MPI = bind_ompi(library)
        elif args.family == "mpich":
            MPI = bind_mpich(library)
    except AttributeError as err:
        logging.error("Binding creation failed: %s", err)
        exit(1)

    world_size = ctypes.c_int()
    world_rank = ctypes.c_int()
    name_len = ctypes.c_int()
    local_sum = ctypes.c_int()
    global_sum = ctypes.c_int()
    processor_name = ctypes.create_string_buffer(MPI.MAX_PROCESSOR_NAME)

    MPI.Init(ctypes.c_int(0), ctypes.c_int(0))
    MPI.Comm_size(MPI.COMM_WORLD, ctypes.byref(world_size))
    MPI.Comm_rank(MPI.COMM_WORLD, ctypes.byref(world_rank))
    MPI.Get_processor_name(processor_name, ctypes.byref(name_len))

    print(
        processor_name.value.decode("utf-8"),
        "-",
        world_rank.value,
        "/",
        world_size.value,
    )

    # Trigger a communication with dummy values to ensure the communication
    # code is loaded, as some libraries do it on the fly
    MPI.Allreduce(
        ctypes.byref(local_sum),
        ctypes.byref(global_sum),
        ctypes.c_int(1),
        MPI.FLOAT,
        MPI.SUM,
        MPI.COMM_WORLD,
    )

    MPI.Barrier(MPI.COMM_WORLD)
    MPI.Finalize()


if __name__ == "__main__":
    main()
