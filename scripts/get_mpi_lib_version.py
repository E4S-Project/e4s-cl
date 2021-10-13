# Script that prints the given mpi's shared library version and distributor
# libmpi.so or equivalent is expected.

import ctypes

lib_path=raw_input("Enter library's path: ")

handle = ctypes.CDLL(lib_path)

version_buffer= ctypes.create_string_buffer(3000)
lenght=ctypes.c_int()

handle.MPI_Get_library_version(version_buffer, ctypes.byref(lenght))
version_buffer_str=version_buffer.value.decode("utf-8")[:500]
print("This shared library belongs to this distribution: \n%s" % version_buffer_str)

