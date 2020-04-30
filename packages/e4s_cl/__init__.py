import os
import sys

__version__ = "0.0.0"
"""str: TAU Commander Version"""

TAUCMDR_VERSION = __version__
"""str: TAU Commander Version"""

EXIT_FAILURE = -100
"""int: Process exit code indicating unrecoverable failure."""

EXIT_WARNING = 100
"""int: Process exit code indicating non-optimal condition on exit."""

EXIT_SUCCESS = 0
"""int: Process exit code indicating successful operation."""

HELP_CONTACT = '<support@paratools.com>'
"""str: E-mail address users should contact for help."""

TAUCMDR_URL = 'www.taucommander.com'
"""str: URL of the TAU Commander project."""

REQUIRED_PYTHON_VERSION = (3, 6)
"""tuple: Required Python version for TAU Comamnder.

A tuple of at least (MAJOR, MINOR) directly comparible to :any:`sys.version_info`
"""

if sys.version_info[0:2] != REQUIRED_PYTHON_VERSION:
    VERSION = '.'.join([str(x) for x in sys.version_info[0:3]])
    EXPECTED = '.'.join([str(x) for x in REQUIRED_PYTHON_VERSION])
    sys.stderr.write("""%s
%s
%s
Your Python version is %s but Python %s is required.
Please install the required Python version or contact %s for support.
""" % (TAUCMDR_URL, sys.executable, sys.version, VERSION, EXPECTED, HELP_CONTACT))
    sys.exit(EXIT_FAILURE)

TAUCMDR_HOME = os.path.realpath(os.path.abspath(os.environ.get('__TAUCMDR_HOME__', 
                                                               os.path.join(os.path.dirname(__file__), '..', '..'))))
"""str: Absolute path to the top-level TAU Commander directory.

This directory contains at least `bin`, `docs`, and `packages` directories and is the root
for system-level package installation paths. **Do not** change it once it is set.
"""

E4S_CL_SCRIPT = os.environ.get('__E4S_CL_SCRIPT__', sys.argv[0])
"""str: Script that launched TAU Commander.

Mainly used for help messages. **Do not** change it once it is set.
"""

SYSTEM_PREFIX = os.path.realpath(os.path.abspath(os.environ.get('__TAUCMDR_SYSTEM_PREFIX__', 
                                                                os.path.join(TAUCMDR_HOME, 'system'))))
"""str: System-level TAU Commander files."""

USER_PREFIX = os.path.realpath(os.path.abspath(os.environ.get('__TAUCMDR_USER_PREFIX__', 
                                                              os.path.join(os.path.expanduser('~'), 
                                                                           '.local', 'e4s_cl'))))
"""str: User-level TAU Commander files."""

PROFILE_DIR = USER_PREFIX
"""str: Name of the project-level directory containing TAU Commander project files."""

def version_banner():
    """Return a human readable text banner describing the TAU Commander installation."""
    import platform
    import socket
    from datetime import datetime
    import e4s_cl.logger
    fmt = ("TAU Commander [ %(url)s ]\n"
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
    data = {"url": TAUCMDR_URL,
            "prefix": TAUCMDR_HOME,
            "version": TAUCMDR_VERSION,
            "timestamp": str(datetime.now()),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "cwd": os.getcwd(),
            "termsize": 'x'.join([str(dim) for dim in e4s_cl.logger.TERM_SIZE]),
            "frozen": getattr(sys, 'frozen', False),
            "python": sys.executable,
            "pyversion": platform.python_version(),
            "pyimpl": platform.python_implementation(),
            "pythonpath": os.pathsep.join(sys.path)}
    return fmt % data
