#!/usr/bin/env python3

import ctypes
from pathlib import Path
from sotools.linker import resolve


class MPIhandles:
    pass


def bind_mpich(libpath: Path) -> object:
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


if __name__ == "__main__":
    MPI = bind_ompi(resolve("libmpi.so.40"))

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
