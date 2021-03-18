import os
import sys

try:
    from e4s_cl.version import __version__, __commit__
except ImportError:
    __version__ = "Undefined"
    __commit__ = "Undefined"
"""str: E4S Container Launcher Version"""

E4S_CL_VERSION = __version__
"""str: E4S Container Launcher Version"""

SCM_COMMIT = __commit__
"""str: Git commit"""

EXIT_FAILURE = -100
"""int: Process exit code indicating unrecoverable failure."""

EXIT_WARNING = 100
"""int: Process exit code indicating non-optimal condition on exit."""

EXIT_SUCCESS = 0
"""int: Process exit code indicating successful operation."""

MIN_PYTHON_VERSION = (3, 6)
"""tuple: Required Python version for E4S Comamnder.

A tuple of at least (MAJOR, MINOR) directly comparible to :any:`sys.version_info`
"""

if sys.version_info[0] < MIN_PYTHON_VERSION[0] or sys.version_info[
        1] < MIN_PYTHON_VERSION[1]:
    VERSION = '.'.join([str(x) for x in sys.version_info[0:3]])
    EXPECTED = '.'.join([str(x) for x in MIN_PYTHON_VERSION])
    sys.stderr.write("""%s
%s
Your Python version is %s but Python %s is required.
Please install the required Python version or raise an issue on Github for support.
""" % (sys.executable, sys.version, VERSION, EXPECTED))
    sys.exit(EXIT_FAILURE)

E4S_CL_HOME = os.path.realpath(
    os.path.abspath(
        os.environ.get('__E4S_CL_HOME__',
                       os.path.join(os.path.dirname(__file__), '..', '..'))))
"""str: Absolute path to the top-level E4S Container Launcher directory.

This directory contains at least `bin`, `docs`, and `packages` directories and is the root
for system-level package installation paths. **Do not** change it once it is set.
"""

E4S_CL_SCRIPT = os.environ.get('__E4S_CL_SCRIPT__', sys.argv[0] or 'e4s-cl')
"""str: Script that launched E4S Container Launcher.

Mainly used for help messages. **Do not** change it once it is set.
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

PROFILE_DIR = USER_PREFIX
"""str: Name of the project-level directory containing E4S Container Launcher project files."""


def version_banner():
    """Return a human readable text banner describing the E4S Container Launcher installation."""
    import platform
    import socket
    from datetime import datetime
    import e4s_cl.logger
    fmt = ("E4S Container Launcher\n"
           "\n"
           "Prefix         : %(prefix)s\n"
           "Version        : %(version)s@%(commit)s\n"
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
        "commit": SCM_COMMIT,
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
