"""containers module

Defines an abstract class to simplify the use of container technology.
Creating an instance of ``Container`` will return a specific class to
the required backend."""

import sys
import json
from importlib import import_module
from pathlib import Path
from e4s_cl import logger, variables
from e4s_cl.util import walk_packages, which
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)

# List of available modules, accessible by their "executable" or cli tool names
EXECUTABLES = {}

# Not used yet, can be used to identify backends by the image's suffix
MIMES = {}


class BackendNotAvailableError(InternalError):
    pass


def dump(func):
    def wrapper(*args, **kwargs):
        # Why isn't it args[0] ?! Python works in mysterious ways
        self = func.__self__

        LOGGER.info("Running %s object:", self.__class__.__name__)
        LOGGER.info("- image: %s", self.image)
        LOGGER.info("- bound: %s",
                    json.dumps([str(path) for path in self.bound], indent=2))
        LOGGER.info("- env: %s", json.dumps(self.env, indent=2))
        LOGGER.info("- LD_PRELOAD: %s", json.dumps(self.ld_preload, indent=2))
        LOGGER.info("- LD_LIBRARY_PATH: %s",
                    json.dumps(self.ld_lib_path, indent=2))

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
        module_name = EXECUTABLES.get(Path(executable).name)
        module = sys.modules.get(module_name)

        if not module_name or not module:
            raise BackendNotAvailableError(
                "Module for backend {} not found".format(module_name))

        driver = object.__new__(module.CLASS)

        # If in debugging mode, print out the config before running
        if variables.is_debug():
            driver.run = dump(driver.run)

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

    def bind_file(self, path, dest=None, options=None):
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
        - The environment variables self.env;
        - The LD_PRELOAD self.ld_preload;
        - The LD_LIBRARY_PATH self.ld_lib_path
        and set them to be available in the created container.
        """
        raise InternalError("run not implemented for container %s" %
                            self.__class__.__name__)


for _, module_name, _ in walk_packages(__path__, prefix=__name__ + "."):
    import_module(module_name)
    module = sys.modules[module_name]

    for executable in module.EXECUTABLES:
        EXECUTABLES.update({executable: module_name})

    for mimetype in module.MIMES:
        MIMES.update({mimetype: module_name})
