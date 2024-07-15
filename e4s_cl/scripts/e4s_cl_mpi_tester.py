"""
Functions used in the e4s-cl-mpi-tester script
"""

import ctypes
import logging
import sys
from typing import Optional
from pathlib import Path
from argparse import ArgumentParser
from sotools.linker import resolve

DESCRIPTION = """This script will dynamically load the MPI library passed as an \
        argument and run a simple program with it. This serves no purpose by \
        itself and is meant to be traced to list the files an arbitrary MPI \
        library requires to run. If no library is given, the first MPI library \
        found in the environment will be used."""
EPILOG = """Please report any issues to http://github.com/E4S-Project/e4s-cl."""

PARSER = ArgumentParser(
    prog=sys.argv[0],
    description=DESCRIPTION,
    epilog=EPILOG,
)

PARSER.add_argument(
    "library",
    nargs='?',
    default=None,
    help="The MPI shared object to analyze.",
)

PARSER.add_argument(
    "-n",
    "--no-mpi",
    action="store_true",
    help="Disable MPI binding; run an empty program",
)

PARSER.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Trace resolving attempts while searching for the library",
)


class MPIHandles:  #pylint: disable=too-few-public-methods
    """
    Empty class to which MPI function/variable bindings are added as attributes.
    """


def bind_mpich(lib: ctypes.CDLL) -> MPIHandles:
    """
    Add bindings from an MPICH library to a MPIHandles object and return it
    """
    handles = MPIHandles()
    setattr(handles, "Init", getattr(lib, "MPI_Init"))
    setattr(handles, "Comm_size", getattr(lib, "MPI_Comm_size"))
    setattr(handles, "Comm_rank", getattr(lib, "MPI_Comm_rank"))
    setattr(handles, "Get_processor_name",
            getattr(lib, "MPI_Get_processor_name"))
    setattr(handles, "Finalize", getattr(lib, "MPI_Finalize"))
    setattr(handles, "Barrier", getattr(lib, "MPI_Barrier"))
    setattr(handles, "Allreduce", getattr(lib, "MPI_Allreduce"))
    setattr(handles, "COMM_WORLD", ctypes.c_int(0x44000000))
    setattr(handles, "FLOAT", ctypes.c_int(0x4c00040a))
    setattr(handles, "SUM", ctypes.c_int(0x58000003))
    setattr(handles, "MAX_PROCESSOR_NAME", 128)

    return handles


def bind_ompi(lib: ctypes.CDLL) -> MPIHandles:
    """
    Add bindings from an OpenMPI library to a MPIHandles object and return it
    """
    handles = MPIHandles()
    setattr(handles, "Init", getattr(lib, "MPI_Init"))
    setattr(handles, "Comm_size", getattr(lib, "MPI_Comm_size"))
    setattr(handles, "Comm_rank", getattr(lib, "MPI_Comm_rank"))
    setattr(handles, "Get_processor_name",
            getattr(lib, "MPI_Get_processor_name"))
    setattr(handles, "Finalize", getattr(lib, "MPI_Finalize"))
    setattr(handles, "Barrier", getattr(lib, "MPI_Barrier"))
    setattr(handles, "Allreduce", getattr(lib, "MPI_Allreduce"))
    setattr(handles, "COMM_WORLD", getattr(lib, "ompi_mpi_comm_world"))
    setattr(handles, "FLOAT", getattr(lib, "ompi_mpi_float"))
    setattr(handles, "SUM", getattr(lib, "ompi_mpi_op_sum"))
    setattr(handles, "MAX_PROCESSOR_NAME", 256)

    return handles


SONAMES = [
    ("libmpi.so.12", bind_mpich),
    ("libmpi.so.40", bind_ompi),
    ("libmpi_cray.so.12", bind_mpich),
]


def select_bind_library() -> Optional[MPIHandles]:
    for (name, bindgen) in SONAMES:
        path = resolve(name)

        if path:
            libhandle = ctypes.CDLL(path)
            logging.info("Using library '%s'", path)
            return bindgen(libhandle)

    return None


def bind_library(path: Path) -> Optional[MPIHandles]:
    for (name, bindgen) in SONAMES:
        if path.resolve().name.startswith(name):
            libhandle = ctypes.CDLL(path)
            return bindgen(libhandle)

    return None


def main():
    """
    Main routine of the e4s-cl-mpi-tester script
    """
    #pylint: disable=no-member
    args = PARSER.parse_args()

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s",
        )

    if args.no_mpi:
        libc = resolve("libc.so.6")
        ctypes.CDLL(libc)
        return 0

    try:
        #pylint: disable=invalid-name
        if args.library is not None:
            MPI = bind_library(Path(args.library))
        else:
            MPI = select_bind_library()
    except AttributeError as err:
        logging.error("Binding creation failed: %s", err)
        sys.exit(1)

    if MPI is None:
        if args.library is not None:
            logging.error("Failed to bind to the MPI library")
        else:
            logging.error("Failed to find an MPI library")
        sys.exit(1)

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
