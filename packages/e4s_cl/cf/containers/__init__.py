"""containers module

Defines an abstract class to simplify the use of container technology.
Creating an instance of ``Container`` will return a specific class to
the required backend."""

import os
import re
import sys
import json
from importlib import import_module
from pathlib import Path
from e4s_cl import E4S_CL_SCRIPT, logger, variables
from e4s_cl.util import walk_packages, which, unrelative, json_loads
from e4s_cl.cf.version import Version
from e4s_cl.cf.libraries import extract_libc, LibrarySet
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)

# List of available modules, accessible by their "executable" or cli tool names
BACKENDS = {}

# List of available, non-debug backends, for help and completion
EXPOSED_BACKENDS = []

# Used to identify backends by the image's suffix
# list of tuples containing (suffix, backend_name)
MIMES = []


class BackendNotAvailableError(InternalError):
    pass


def dump(func):
    """
    If verbose, output a description of the container about to be run before
    launching it.

    This needs to be a decorator as it is wraps the run() method implemented
    in every backend module.
    """
    def wrapper(*args, **kwargs):
        self = func.__self__

        LOGGER.debug(str(self))

        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


class Container():
    """Abstract class to complete depending on the container tech."""

    # pylint: disable=unused-argument
    def __new__(cls, image=None, executable=None):
        """
        Object level creation hijacking: depending on the executable
        argument, the appropriate subclass will be returned.
        """
        module_name = BACKENDS.get(Path(executable).name)
        module = sys.modules.get(module_name)

        if not module_name or not module:
            raise BackendNotAvailableError(
                "Module for backend {} not found".format(module_name))

        driver = object.__new__(module.CLASS)

        # If in debugging mode, print out the config before running
        if logger.debug_mode():
            driver.run = dump(driver.run)
        driver.__str__ = dump(driver.__str__)

        return driver

    def __init__(self, image=None, executable=None):
        """
        Common class init: this code is run in the actual sub-classes
        """
        self.executable = which(executable)

        if not self.executable or (not Path(self.executable).exists()):
            raise BackendNotAvailableError("Executable %s not found" %
                                           executable)

        # Container image file on the host
        self.image = image

        # User-set parameters
        self.bound = []  # Files to bind (host_path, guest_path, options)
        self.env = {}  # Environment
        self.ld_preload = []  # Files to put in LD_PRELOAD
        self.ld_lib_path = []  # Directories to put in LD_LIBRARY_PATH

        # Container analysis attributes
        self._libc_ver = None

    def get_data(self, entrypoint, library_set=LibrarySet()):
        """
        Run the e4s-cl analyze command in the container to analyze the environment
        inside of it. The results will be used to tailor the library import
        to ensure compatibility of the shared objects.
        """
        fdr, fdw = os.pipe()
        os.set_inheritable(fdw, True)
        self.bind_env_var('__E4S_CL_JSON_FD', str(fdw))

        entrypoint.command = [E4S_CL_SCRIPT, 'analyze', '--libraries'] + list(
            library_set.sonames)
        script_name = entrypoint.setUp()

        code, _ = self.run([script_name], redirect_stdout=False)

        entrypoint.tearDown()

        if code:
            raise InternalError("Could not determine container's content !")

        data = json_loads(os.read(fdr, 1024**3).decode())

        self.libc_v = Version(data.get('libc_version', '0.0.0'))
        self.libraries = data.get('libraries', LibrarySet())

    def bind_file(self, path, dest=None, options=None):
        """
        If there is no destination, handle files with relative paths.
        For instance on summit, some files are required as
        /jsm_pmix/container/../lib/../bin/file
        Although only /jsm_pmix/bin/file is required, not
        having jsm_pmix/container && lib makes it error out
        unrelative returns a list of all the paths required for such a file
        """
        if not dest:
            for _path in unrelative(path):
                self.bound.append((_path, None, options))
        else:
            self.bound.append((path, dest, options))

    def bind_env_var(self, key, value):
        self.env.update({key: value})

    def add_ld_preload(self, path):
        if path not in self.ld_preload:
            self.ld_preload.append(path)

    def add_ld_library_path(self, path):
        if path not in self.ld_lib_path:
            self.ld_lib_path.append(path)

    def run(self, command, redirect_stdout=False):
        """
        run a command in a container.

        command         list[str]   the command line to execute
        redirect_stdout bool        if true, return the output as a string;
                                    if false, it ends up on stdout

        This method must be implemented in the container module.
        It should take into account the parameters set in the object:
        - The bound files in self.bound;
        - The environment variables self.env;
        - The LD_PRELOAD self.ld_preload;
        - The LD_LIBRARY_PATH self.ld_lib_path
        and set them to be available in the created container.

        It should return a tuple the process' returncode and output
        """
        raise NotImplementedError(
            "`run` method not implemented for container module %s" %
            self.__class__.__name__)

    def __str__(self):
        out = []
        out.append("%s object:" % self.__class__.__name__)
        if self.image:
            out.append("- image: %s" % self.image)
        if self.bound:
            out.append("- bound: %s" %
                       json.dumps([str(path)
                                   for path in self.bound], indent=2))
        if self.env:
            out.append("- env: %s" % json.dumps(self.env, indent=2))
        if self.ld_preload:
            out.append("- LD_PRELOAD: %s" %
                       json.dumps(self.ld_preload, indent=2))
        if self.ld_lib_path:
            out.append("- LD_LIBRARY_PATH: %s" %
                       json.dumps(self.ld_lib_path, indent=2))
        return '\n'.join(out)


def guess_backend(path):
    suffix = Path(path).suffix

    matches = list(filter(lambda x: x[0] == suffix, MIMES))

    # If we cannot associate a unique backend to a MIME
    if len(matches) != 1:
        return

    return matches[0][1]


for _, _module_name, _ in walk_packages(__path__, prefix=__name__ + "."):
    import_module(_module_name)
    _module = sys.modules[_module_name]

    for _executable in _module.EXECUTABLES:
        BACKENDS.update({
            _executable: _module_name,
        })

        if not getattr(_module, 'DEBUG_BACKEND', False):
            EXPOSED_BACKENDS.append(_executable)

    for mimetype in _module.MIMES:
        MIMES.append((mimetype, _module.NAME))
