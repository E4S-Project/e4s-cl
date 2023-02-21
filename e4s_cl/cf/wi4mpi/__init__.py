"""
Module housing support for WI4MPI compatibility
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache
from e4s_cl import logger
from e4s_cl.cf.detect_mpi import MPIIdentifier, library_install_dir
from e4s_cl.cf.containers import Container
from e4s_cl.cf.launchers import filter_arguments, Parser
from e4s_cl.cf.launchers.mpirun import _wi4mpi_options

LOGGER = logger.get_logger(__name__)


@dataclass(frozen=True)
class MPIFamily:
    """
    Dataclass to have compact objects with MPI vendor metadata
    """
    # Vendor name, as returned in MPIIdentifier
    vendor_name: str
    # Name used by wi4mpi on the command line
    cli_name: str
    # Name used by wi4mpi in the environment
    env_name: str
    # Wi4MPI's environment variable for this family
    path_key: str
    # Wi4MPI's default environment variable for this family
    default_path_key: str
    # Default soname for this vendor's C library
    mpi_c_soname: str
    # Default soname for this vendor Fortran library
    mpi_f_soname: str

    def __str__(self):
        return self.cli_name


# MPI vendor libraries metadata. On top of the different MPI families, some
# vendors adopt standard paths different from the norm. This collection keeps
# track of all metadata for each of those vendors.
WI4MPI_METADATA = [
    MPIFamily(
        vendor_name='Intel(R) MPI',
        cli_name='intelmpi',
        env_name='INTEL',
        path_key='INTELMPI_ROOT',
        default_path_key='INTELMPI_DEFAULT_ROOT',
        mpi_c_soname='libmpi.so',
        mpi_f_soname='libmpifort.so',
    ),
    MPIFamily(
        vendor_name='Open MPI',
        cli_name='openmpi',
        env_name='OMPI',
        path_key='OPENMPI_ROOT',
        default_path_key='OPENMPI_DEFAULT_ROOT',
        mpi_c_soname='libmpi.so',
        mpi_f_soname='libmpi_mpifh.so',
    ),
    MPIFamily(
        vendor_name='MPICH',
        cli_name='mpich',
        env_name='MPICH',
        path_key='MPICH_ROOT',
        default_path_key='MPICH_DEFAULT_ROOT',
        mpi_c_soname='libmpi.so',
        mpi_f_soname='libmpifort.so',
    ),
    MPIFamily(
        vendor_name='CRAY MPICH',
        cli_name='mpich',
        env_name='MPICH',
        path_key='MPICH_ROOT',
        default_path_key='MPICH_DEFAULT_ROOT',
        mpi_c_soname='libmpi_cray.so',
        mpi_f_soname='libmpifort_cray.so',
    ),
]

# Keys used to describe MPI families. Wi4MPI is needed if a pair of those keys
# is present in the SUPPORTED_TRANSLATIONS collection
WI4MPI_SOURCES = set(map(lambda x: x.cli_name,
                         WI4MPI_METADATA)) | {'interface'}

SUPPORTED_TRANSLATIONS = {
    ('intelmpi', 'openmpi'),
    ('interface', 'intelpmi'),
    ('interface', 'mpich'),
    ('interface', 'openmpi'),
    ('mpich', 'openmpi'),
    ('openmpi', 'intelpmi'),
    ('openmpi', 'mpich'),
    ('openmpi', 'openmpi'),
}

_FAMILY_ENV_VARS = set(map(lambda x: x.path_key, WI4MPI_METADATA))

# Set of all environment variables used by Wi4MPI, to pass to the underlying code
WI4MPI_ENVIRONMENT_VARIABLES = {
    'WI4MPI_ROOT',
    'WI4MPI_FROM',
    'WI4MPI_TO',
    'WI4MPI_RUN_MPI_C_LIB',
    'WI4MPI_RUN_MPI_F_LIB',
    'WI4MPI_RUN_MPIIO_C_LIB',
    'WI4MPI_RUN_MPIIO_F_LIB',
} | _FAMILY_ENV_VARS


def wi4mpi_identify(value: str) -> Optional[MPIFamily]:
    for family in WI4MPI_METADATA:
        if value.lower() in {
                family.vendor_name.lower(),
                family.cli_name.lower()
        }:
            return family
    return None


def wi4mpi_qualifier(value: MPIIdentifier) -> Optional[str]:
    if not isinstance(value, MPIIdentifier):
        return None
    match = wi4mpi_identify(value.vendor)
    if match:
        return match.cli_name
    return None


def wi4mpi_get_metadata(value: MPIIdentifier) -> Optional[MPIFamily]:
    if not isinstance(value, MPIIdentifier):
        return None
    match = wi4mpi_identify(value.vendor)
    if match:
        return match
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
        matches = set(filter(lambda x: x.env_name == env_name,
                             WI4MPI_METADATA))
        if len(matches) == 1:
            distribution_data = matches.pop()

            config_value = config.get(distribution_data.default_path_key, "")

            return Path(config_value, 'lib', 'libmpi.so')
        return None

    source_lib = _get_lib(source)
    target_lib = _get_lib(target)

    return list(
        filter(lambda x: x.resolve().exists(),
               filter(None, [wrapper_lib, source_lib, target_lib])))


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


def wi4mpi_find_libraries(
        target: MPIFamily,
        mpi_libraries: List[Path]) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Find the target's required MPI libraries from the paths in mpi_libraries
    """

    def locate(soname: str, available: List[Path]) -> Optional[Path]:
        """
        Find the library with the given soname, either from the libraries
        passed in the list or from the directories they are in
        """
        matches = set(filter(lambda x: x.name.startswith(soname), available))
        search_directories = set(map(lambda x: x.resolve().parent, available))

        # If a match exists in the given libraries
        if matches:
            return matches.pop()

        # Search the libraries' directories for the soname
        for directory in search_directories:
            matches = set(directory.glob(f"{soname}*"))
            if matches:
                return matches.pop()

        LOGGER.debug(
            "Failed to locate %(soname)s in %(directories)s",
            {
                "soname": soname,
                "directories": search_directories,
            },
        )

        return None

    # Find the entry C and Fortran MPI libraries
    run_c_lib = locate(target.mpi_c_soname, mpi_libraries)
    run_f_lib = locate(target.mpi_f_soname, mpi_libraries)

    return (run_c_lib, run_f_lib)


def wi4mpi_prepare_environment_preload(
    wi4mpi_install_dir: Path,
    from_: str,
    target: MPIFamily,
    target_install_dir: Path,
    run_c_lib: Path,
    run_f_lib: Path,
):
    """
    Prepare the environment for a Wi4MPI execution in preload mode
    Updates the environment variables:
      + WI4MPI_ROOT
      + WI4MPI_FROM
      + WI4MPI_TO
      + <LIBRARY>_ROOT
      + WI4MPI_RUN_MPI_C_LIB
      + WI4MPI_RUN_MPI_F_LIB
      + WI4MPI_RUN_MPIIO_C_LIB
      + WI4MPI_RUN_MPIIO_F_LIB
    """

    env = {
        'WI4MPI_ROOT': str(wi4mpi_install_dir),
        target.path_key: str(target_install_dir),
        'WI4MPI_FROM': str(from_),
        'WI4MPI_TO': str(target.cli_name),
        'WI4MPI_RUN_MPI_C_LIB': str(run_c_lib),
        'WI4MPI_RUN_MPI_F_LIB': str(run_f_lib),
        'WI4MPI_RUN_MPIIO_C_LIB': str(run_c_lib),
        'WI4MPI_RUN_MPIIO_F_LIB': str(run_f_lib),
    }

    for key, value in env.items():
        LOGGER.debug("Wi4MPI preload: %s=%s", key, value)
        os.environ[key] = value


def wi4mpi_prepare_environment_interface(
    wi4mpi_install_dir: Path,
    target: MPIFamily,
    target_install_dir: Path,
    run_c_lib: Path,
    run_f_lib: Path,
):
    """
    Prepare the environment for a Wi4MPI execution in interface mode
    Updates the environment variables:
      + WI4MPI_ROOT
      + WI4MPI_TO
      + <LIBRARY>_ROOT
      + WI4MPI_RUN_MPI_C_LIB
      + WI4MPI_RUN_MPI_F_LIB
      + WI4MPI_RUN_MPIIO_C_LIB
      + WI4MPI_RUN_MPIIO_F_LIB
    """

    env = {
        'WI4MPI_ROOT': str(wi4mpi_install_dir),
        target.path_key: str(target_install_dir),
        'WI4MPI_TO': str(target.cli_name),
        'WI4MPI_RUN_MPI_C_LIB': str(run_c_lib),
        'WI4MPI_RUN_MPI_F_LIB': str(run_f_lib),
        'WI4MPI_RUN_MPIIO_C_LIB': str(run_c_lib),
        'WI4MPI_RUN_MPIIO_F_LIB': str(run_f_lib),
    }

    for key, value in env.items():
        LOGGER.debug("Wi4MPI interface: %s=%s", key, value)
        os.environ[key] = value
