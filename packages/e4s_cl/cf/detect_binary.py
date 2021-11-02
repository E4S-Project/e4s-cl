import os
from e4s_cl import USER_PREFIX
from e4s_cl.cf.libraries.linker import resolve

BINARY_DIR = os.path.join(USER_PREFIX, 'compiled_binaries')

binary_dict = {
    '40': ['Open MPI', "openmpi_binary"],
    '12': ['MPICH', "mpich_binary"]
    #'Spectrum MPI': ,
    #'Intel(R) MPI': ,
    #'CRAY MPICH': ,
    #'MVAPICH': 
}


def select_binary():
    libso_path = resolve("libmpi.so")

    (launcher_path, compiler_path, libso_vers, binary_path) = ("", "", "", "")
    if libso_path is not None:
        launcher_path = os.path.join(libso_path.split("lib",1)[0], 'bin/mpirun')
        compiler_path = os.path.join(libso_path.split("lib",1)[0], 'bin/mpicc')
        libso_vers = libso_path.split(".so.",1)[1].split(".",1)[0]
        binary_path = os.path.join(BINARY_DIR, binary_dict[libso_vers][1])

    paths = [binary_path, launcher_path, compiler_path]

    return paths
