import os
from e4s_cl import USER_PREFIX
from e4s_cl.cf.libraries.linker import resolve

BINARY_DIR = os.path.join(USER_PREFIX, 'compiled_binaries')

binary_dict = {
    '40': ['Open MPI', "mpich_binary"],
    '12': ['MPICH', "openmpi_binary"]
    #'Spectrum MPI': ,
    #'Intel(R) MPI': ,
    #'CRAY MPICH': ,
    #'MVAPICH': 
}


def select_binary():
    libso_vers = resolve("libmpi.so").split(".so.",1)[1].split(".",1)[0]
    
    binary_path = os.path.join(BINARY_DIR, binary_dict[libso_vers][1])
    
    return binary_path
