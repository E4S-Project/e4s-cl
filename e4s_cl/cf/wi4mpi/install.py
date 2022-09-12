import os
import subprocess
from pathlib import Path
from git import Repo
from e4s_cl.logger import get_logger
from e4s_cl.cf.detect_name import _get_mpi_vendor_version, filter_mpi_libs

LOGGER = get_logger(__name__)

WI4MPI_DIR = Path(os.path.expanduser('~/.local/share/wi4mpi'))

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
    nofail = True
    wi4mpi_url = "https://github.com/cea-hpc/wi4mpi.git"
    repo_dir = WI4MPI_DIR
    build_dir = repo_dir / "BUILD"
    cmakeCmd = ['cmake', \
            '-DCMAKE_INSTALL_PREFIX=~/.local/wi4mpi', \
            '-DWI4MPI_COMPILER=GNU', '..']
    makeCmd = ['make', '-j', '4']
    makeInstallCmd = ['make', 'install']

    def _run_wi4mpi_install_cmd(cmd):
        with subprocess.Popen(cmd) as proc:
            if proc.wait():
                LOGGER.warning(
                    f"Wi4mpi installation failed. Proceeding with profile initialisation"
                )
                return False
            return True

    if not os.path.exists(repo_dir):
        Repo.clone_from(wi4mpi_url, repo_dir)
        LOGGER.warning(f"Cloned wi4mpi repo at {repo_dir}")

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
        nofail = _run_wi4mpi_install_cmd(makeCmd)
        if nofail:
            nofail = _run_wi4mpi_install_cmd(makeInstallCmd)

    if nofail:
        LOGGER.warning(f"Wi4mpi is built and installed")

    return nofail
