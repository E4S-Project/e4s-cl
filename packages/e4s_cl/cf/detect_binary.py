import os
from pathlib import Path
from e4s_cl import USER_PREFIX
from e4s_cl import logger, util
from e4s_cl.cf.libraries.linker import resolve

LOGGER = logger.get_logger(__name__)

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
    # Finds the available libmpi.so
    libso_path = resolve("libmpi.so")

    (launcher_path, compiler_path, libso_vers, binary_path) = ("", "", "", "")

    # Builds the different paths for laucher/compiler for the profile data
    if libso_path is not None:
        launcher_path = os.path.join(libso_path.split("lib",1)[0], 'bin/mpirun')
        compiler_path = os.path.join(libso_path.split("lib",1)[0], 'bin/mpicc')
        libso_vers = libso_path.split(".so.",1)[1].split(".",1)[0]
    
    # Update binary path if version is supported
    if libso_vers in binary_dict.keys():
        binary_path = os.path.join(BINARY_DIR, binary_dict[libso_vers][1])
    else:
        LOGGER.debug("MPI vendor not supported by precompiled binary initialisation\nProceeding with legacy initialisation")
    
    if not Path(binary_path).exists():
        binary_path = ""
    
    paths = [binary_path, launcher_path, compiler_path]
    return paths
