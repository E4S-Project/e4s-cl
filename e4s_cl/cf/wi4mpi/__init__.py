"""
Module housing support for WI4MPI compatibility
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
from functools import lru_cache
from e4s_cl import logger
from e4s_cl.cf.detect_mpi import MPIIdentifier
from e4s_cl.cf.containers import Container
from e4s_cl.cf.launchers import filter_arguments, Parser
from e4s_cl.cf.launchers.mpirun import _wi4mpi_options

LOGGER = logger.get_logger(__name__)


@dataclass(frozen=True)
class MPIDistribution:
    cli_name: str
    env_name: str
    path_key: str


_MPI_DISTRIBUTIONS = {
    'Intel(R) MPI': MPIDistribution('intelmpi', 'INTEL',
                                    'INTELMPI_DEFAULT_ROOT'),
    'Open MPI': MPIDistribution('openmpi', 'OMPI', 'OPENMPI_DEFAULT_ROOT'),
    'MPICH': MPIDistribution('mpich', 'MPICH', 'MPICH_DEFAULT_ROOT'),
}


def wi4mpi_qualifier(value: MPIIdentifier) -> Optional[str]:
    match = _MPI_DISTRIBUTIONS.get(value.vendor)
    if match:
        return match.cli_name
    return None


def wi4mpi_enabled() -> bool:
    # Convoluted way to have True or False instead of the contents of the key
    return not os.environ.get("WI4MPI_VERSION") is None


@lru_cache()
def wi4mpi_root() -> Optional[Path]:
    string = os.environ.get("WI4MPI_ROOT")

    if string is None or not string:
        LOGGER.debug("Getting Wi4MPI root failed")
        return None

    return Path(string)


def __read_cfg(cfg_file: Path) -> Dict[str, str]:
    config = {}

    try:
        with open(cfg_file, 'r', encoding='utf-8') as cfg:
            for line in cfg.readlines():
                line = line.strip()

                if line.startswith('#') or not '=' in line:
                    continue

                key, value = line.split('=')

                config.update({key: value.strip('"')})

    except OSError as err:
        LOGGER.debug("Error accessing configuration %s: %s",
                     cfg_file.as_posix(), str(err))

    return config


@lru_cache()
def wi4mpi_config(install_dir: Path) -> Dict[str, str]:
    global_cfg = __read_cfg(install_dir / 'etc' / 'wi4mpi.cfg')
    user_cfg = __read_cfg(Path.home() / '.wi4mpi.cfg')

    global_cfg.update(user_cfg)

    return global_cfg


def wi4mpi_import(container: Container, install_dir: Path) -> None:
    """
    Bind to a container the necessary files required for wi4mpi to run
    """
    container.bind_file(install_dir.as_posix())

    config = wi4mpi_config(install_dir)

    for (key, value) in config.items():
        if 'ROOT' in key and value:
            container.bind_file(value)
            container.add_ld_library_path(
                Path(value).joinpath('lib').as_posix())


def wi4mpi_libraries(install_dir: Path) -> List[Path]:
    """
    Use the environment to output a list of libraries required by wi4mpi
    """
    config = wi4mpi_config(install_dir)

    source = os.environ.get("WI4MPI_FROM", "")
    target = os.environ.get("WI4MPI_TO", "")

    if not (source and target):
        LOGGER.debug(
            "Error getting WI4MPI libraries: Missing environment variables")
        return []

    wrapper_lib = Path(install_dir, 'libexec', 'wi4mpi',
                       f"libwi4mpi_{source}_{target}.so")

    def _get_lib(env_name: str) -> Optional[Path]:
        matches = set(
            filter(lambda x: x.env_name == env_name,
                   _MPI_DISTRIBUTIONS.values()))
        if len(matches) == 1:
            distribution_data = matches.pop()

            config_value = config.get(distribution_data.path_key, "")

            return Path(config_value, 'lib', 'libmpi.so')
        return None

    source_lib = _get_lib(source)
    target_lib = _get_lib(target)

    return list(
        filter(lambda x: x.resolve().exists(),
               [wrapper_lib, source_lib, target_lib]))


def wi4mpi_libpath(install_dir: Path):
    """
    Select all WI4MPI-relevant elements from the LD_LIBRARY_PATH
    """
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', '').split(':')

    for filename in ld_library_path:
        if install_dir.as_posix() in filename:
            yield Path(filename)


def wi4mpi_preload(install_dir: Path) -> List[str]:
    """
    Returns a list of libraries to preload for WI4MPI
    """
    to_preload = []

    # Pass along the preloaded libraries from wi4mpi
    for file in os.environ.get("LD_PRELOAD", "").split():
        to_preload.append(file)

    source = os.environ.get("WI4MPI_FROM", "")

    fakelib_dir = install_dir / 'libexec' / 'wi4mpi' / f"fakelib{source}"

    if fakelib_dir.exists():
        for file in fakelib_dir.glob('lib*'):
            to_preload.append(file.as_posix())

    return to_preload


def wi4mpi_adapt_arguments(cmd_line: List[str]) -> List[str]:
    """Quote arguments destined to the implementation mpirun in an --extra block"""
    launcher = None
    arguments = cmd_line
    if cmd_line[0] == 'mpirun':
        launcher = 'mpirun'
        arguments = cmd_line[1:]

    wi4mpi, mpi = filter_arguments(Parser(_wi4mpi_options), arguments)
    extra = []
    if mpi:
        extra = ['-E', " ".join(mpi)]

    return list(filter(None, [launcher, *wi4mpi, *extra]))
