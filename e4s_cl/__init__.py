import os
import sys
from pathlib import Path
try:
    from e4s_cl.version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.0"

E4S_CL_VERSION = __version__
"""str: E4S Container Launcher Version"""

EXIT_FAILURE = -100
"""int: Process exit code indicating unrecoverable failure."""

EXIT_WARNING = 100
"""int: Process exit code indicating non-optimal condition on exit."""

EXIT_SUCCESS = 0
"""int: Process exit code indicating successful operation."""

INIT_TEMP_PROFILE_NAME = '__INIT_TEMP_PROFILE'
"""string: Default profile name at initialisation."""

MIN_PYTHON_VERSION = (3, 6)
"""tuple: Required Python version for E4S Container Launcher.

A tuple of at least (MAJOR, MINOR) directly comparible to :any:`sys.version_info`
"""

PYTHON_VERSION = sys.version_info[0:3]
"""list: Version of the running python interpreter"""

if sys.version_info[0] < MIN_PYTHON_VERSION[0] or sys.version_info[
        1] < MIN_PYTHON_VERSION[1]:
    VERSION = '.'.join([str(x) for x in sys.version_info[0:3]])
    EXPECTED = '.'.join([str(x) for x in MIN_PYTHON_VERSION])
    sys.stderr.write(f"""{sys.executable}
{sys.version}
Your Python version is {VERSION} but Python {EXPECTED} is required.
Please install the required Python version or raise an issue on Github for support.
""")
    sys.exit(EXIT_FAILURE)

E4S_CL_TEST = bool(os.environ.get('__E4S_CL_TEST__', False))
"""bool: True if the package is run in a test environment"""

# Use a file to brand installation directories
_HOME_MARKER = '.e4s-cl-home'
__install_home = None

# Look at all the parent of the package to look for the marker
for parent in Path(__file__).resolve().parents:
    if Path(parent, _HOME_MARKER).exists():
        __install_home = parent

E4S_CL_HOME = Path(
    os.environ.get('__E4S_CL_HOME__', __install_home
                   or Path(__file__).parents[1])).resolve().as_posix()
"""str: Absolute path to the top-level E4S Container Launcher directory.

This directory contains at least `bin` and `conda` directories and is the root
for system-level package installation paths. **Do not** change it once it is set.
"""

E4S_CL_ENV_PREFIX = 'E4S_CL'

E4S_CL_SCRIPT = os.environ.get('__E4S_CL_SCRIPT__', sys.argv[0] or 'e4s-cl')
"""str: Script that launched E4S Container Launcher.

Mainly used for help messages. **Do not** change it once it is set.
"""

E4S_CL_MPI_TESTER_SCRIPT_NAME = "e4s-cl-mpi-tester"
"""str: Name of the MPI tester script bundled with e4s-cl.
"""

SYSTEM_PREFIX = os.path.realpath(
    os.path.abspath(
        os.environ.get('__E4S_CL_SYSTEM_PREFIX__',
                       os.path.join(E4S_CL_HOME, 'system'))))
"""str: System-level E4S Container Launcher files."""

USER_PREFIX = os.path.realpath(
    os.path.abspath(
        os.environ.get(
            '__E4S_CL_USER_PREFIX__',
            os.path.join(os.path.expanduser('~'), '.local', 'e4s_cl'))))
"""str: User-level E4S Container Launcher files."""

CONTAINER_DIR = Path("/", ".e4s-cl").as_posix()
"""str: Path of a directory in which to bind files when in containers"""

CONTAINER_SCRIPT = Path(CONTAINER_DIR, "script").as_posix()
"""str: Path of the script to execute in the container"""

BAREBONES_LIBRARY_DIR = Path(USER_PREFIX, "barebones_libraries").as_posix()
"""str: Path of the script to execute in the use of the barebones backend"""

BAREBONES_SCRIPT = Path(BAREBONES_LIBRARY_DIR, "barebones_script").as_posix()
"""str: Path of the script to execute in the use of the barebones backend"""

CONTAINER_LIBRARY_DIR = Path(CONTAINER_DIR, "hostlibs").as_posix()
"""str: Path of the libraries bound in the container"""

CONTAINER_BINARY_DIR = Path(CONTAINER_DIR, "executables").as_posix()
"""str: Path of the libraries bound in the container"""

PROFILE_LIST_DEFAULT_COLUMNS = ["selected", "name", "backend", "image"]
"""list[str] columns to display in profile list by default"""

WI4MPI_DIR = Path(USER_PREFIX) / "wi4mpi"
"""Directory in which Wi4MPI releases and build will be put if needed"""

WI4MPI_DEFAULT_INSTALL_DIR = WI4MPI_DIR / 'install'
"""Default installation directory for Wi4MPI"""


def version_banner():
    """Return a human readable text banner describing the E4S Container Launcher installation."""
    import platform
    import socket
    from datetime import datetime
    import e4s_cl.logger
    fmt = ("E4S Container Launcher [ http://e4s-project.github.io/e4s-cl ]\n"
           "\n"
           "Prefix         : %(prefix)s\n"
           "Version        : %(version)s\n"
           "Timestamp      : %(timestamp)s\n"
           "Hostname       : %(hostname)s\n"
           "Platform       : %(platform)s\n"
           "Working Dir.   : %(cwd)s\n"
           "Terminal Size  : %(termsize)s\n"
           "Frozen         : %(frozen)s\n"
           "Python         : %(python)s\n"
           "Python Version : %(pyversion)s\n"
           "Python Impl.   : %(pyimpl)s\n"
           "PYTHONPATH     : %(pythonpath)s\n")
    data = {
        "prefix": E4S_CL_HOME,
        "version": E4S_CL_VERSION,
        "timestamp": str(datetime.now()),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "termsize": 'x'.join([str(dim) for dim in e4s_cl.logger.TERM_SIZE]),
        "frozen": getattr(sys, 'frozen', False),
        "python": sys.executable,
        "pyversion": platform.python_version(),
        "pyimpl": platform.python_implementation(),
        "pythonpath": os.pathsep.join(sys.path)
    }
    return fmt % data
