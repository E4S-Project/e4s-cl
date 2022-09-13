import os
import subprocess
from subprocess import DEVNULL, STDOUT
from pathlib import Path
from git import Repo
from e4s_cl import E4S_CL_HOME
from e4s_cl.logger import get_logger
from e4s_cl.util import which
from e4s_cl.cf.detect_name import _get_mpi_vendor_version, filter_mpi_libs

LOGGER = get_logger(__name__)

WI4MPI_DIR = Path(E4S_CL_HOME) / "wi4mpi"

def _install_wi4mpi():
    return install_wi4mpi()


def _nop():
    pass


DISTRO_DICT = {
    'Intel(R) MPI': _nop,
    'Open MPI': _install_wi4mpi,
    'Spectrum MPI': _nop,
    'CRAY MPICH': _nop,
    'MPICH': _nop,
    'MVAPICH': _nop
}


def check_wi4mpi(profile):
    """
    Checks if the mpi vendor detected needs wi4mpi in order to function
    correctly with e4s-cl, and if so installs it.
    """
    installed = False
    mpi_libs = filter_mpi_libs(profile)
    vendor_list = list(filter(None, map(_get_mpi_vendor_version, mpi_libs)))
    if vendor_list:
        vendor = vendor_list[0][0]
        installed = DISTRO_DICT.get(vendor)()
    return installed


def install_wi4mpi():
    """Clones and installs wi4mpi from git run
    
    Installs in ~/.local/share/wi4mpi using a GNU compiler
    
    """

    if not which("cmake"):
        LOGGER.warning(
                "WI4MPI installation failed: cmake is missing. Proceeding with profile initialisation"
        )
        return False
    nofail = True
    wi4mpi_url = "https://github.com/cea-hpc/wi4mpi.git"
    repo_dir = WI4MPI_DIR
    build_dir = repo_dir / "BUILD"
    cmakeCmd = ['cmake', \
            '-DCMAKE_INSTALL_PREFIX=~/.local/wi4mpi', \
            '-DWI4MPI_COMPILER=GNU', '..']
    makeCmd = ['cmake', '--build', '.', '--parallel', '-t', 'install']
    makeInstallCmd = ['make', 'install']

    def _run_wi4mpi_install_cmd(cmd, discard_output=True):

        stdout = None
        stderr = None
        if discard_output:
            stdout = DEVNULL
            stderr = STDOUT

        with subprocess.Popen(cmd, stdout=stdout, stderr=stderr) as proc:
            if proc.wait():
                if discard_output:
                    LOGGER.warning(
                        "WI4MPI installation failed. Retrying"
                    )
                    nofail = _run_wi4mpi_install_cmd(cmd, discard_output=False)
                if not nofail:
                    LOGGER.warning(
                        "WI4MPI installation failed. Proceeding with profile initialisation"
                    )
                    return False
            return True

    if not os.path.exists(repo_dir):
        Repo.clone_from(wi4mpi_url, repo_dir)
        LOGGER.warning(f"Cloned WI4MPI repo at {repo_dir}")

    try:
        build_dir.mkdir(exist_ok=True)
        os.chdir(build_dir)
    except PermissionError as err:
        LOGGER.debug("Failed to create directory %s: %s", build_dir.as_posix(),
                     str(err))
        nofail = False
        return nofail

    if nofail and not os.path.exists(build_dir / "Makefile"):
        nofail = _run_wi4mpi_install_cmd(cmakeCmd)

    if nofail and not os.path.exists(build_dir / "install_manifest.txt"):
        LOGGER.warning(
                "Installing WI4MPI"
        )
        nofail = _run_wi4mpi_install_cmd(makeCmd)
        #if nofail:
         #   nofail = _run_wi4mpi_install_cmd(makeInstallCmd)

    if nofail:
        LOGGER.warning(f"WI4MPI is built and installed")

    return nofail
