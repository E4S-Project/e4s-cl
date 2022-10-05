"""
Defines an abstract class to simplify the use of container technology.
Creating an instance of ``Container`` will return a specific class to
the required backend.

To implement support for a new container backend, create a submodule
that posesses the following attributes:
    - NAME: The name identifying the backend
    - EXECUTABLES: List of executables the backend uses; if not accessible on the
        PATH, the backend will be disabled
    - MIMES: if the backend uses files, extensions used to guess the backend from
        an image
    - CLASS: the class to use. The class' `run` method will be used when launching
        the container: refer to its docstring for details
"""

import os
import re
import sys
import json
from dataclasses import dataclass
from importlib import import_module
from tempfile import TemporaryFile, NamedTemporaryFile
from pathlib import Path
from typing import Union, List, Tuple, Iterable, Optional
from sotools.dl_cache import cache_libraries, get_generator
from e4s_cl.logger import get_logger, debug_mode
from e4s_cl import (EXIT_FAILURE, CONTAINER_DIR, CONTAINER_LIBRARY_DIR,
                    CONTAINER_BINARY_DIR, CONTAINER_SCRIPT)
from e4s_cl.variables import ParentStatus
from e4s_cl.util import (walk_packages, which, json_loads,
                         run_e4scl_subprocess, path_contains)
from e4s_cl.cf.version import Version
from e4s_cl.error import ConfigurationError

LOGGER = get_logger(__name__)

# List of available modules, accessible by their "executable" or cli tool names
BACKENDS = {}

# List of available, non-debug backends, for help and completion
EXPOSED_BACKENDS = []

# Used to identify backends by the image's suffix
# list of tuples containing (suffix, backend_name)
MIMES = []


# pylint: disable=too-few-public-methods
class FileOptions:
    """
    Abstraction of bound files options
    """
    READ_ONLY = 0
    READ_WRITE = 1


@dataclass(frozen=True)
class BoundFile:
    """Element of the bound file dictionnary"""
    origin: Path
    destination: Path
    option: int


class BackendError(ConfigurationError):
    """Error raised when the requested container tech is not available"""

    def __init__(self, backend_name):
        self.offending = backend_name
        self._message = f"An error has been encountered setting up the container technology backend {backend_name}."
        super().__init__(self._message)

    def handle(self, etype, value, tb):
        LOGGER.critical(self._message)
        return EXIT_FAILURE


class BackendNotAvailableError(BackendError):
    """Error raised when the requested backend is not found on the system"""

    def __init__(self, backend_name):
        super().__init__(backend_name)
        self._message = f"Backend {self.offending} not found. Is the module loaded ?"


class BackendUnsupported(BackendError):
    """Error raised when the requested backend is not supported"""

    def __init__(self, backend_name):
        super().__init__(backend_name)
        pretty = 's are' if len(EXPOSED_BACKENDS) > 1 else ' is'
        self._message = f"""Backend {self.offending} not supported at this time.
The available backend{pretty}: {", ".join(EXPOSED_BACKENDS)}.
Please create a GitHub issue if support is required."""


class AnalysisError(ConfigurationError):
    """Generic error for container analysis failure"""

    def __init__(self, returncode):
        self.code = returncode
        super().__init__(f"Container analysis failed ! ({self.code})")

    def handle(self, etype, value, tb):
        LOGGER.critical("Container analysis failed ! (%d)", self.code)
        return EXIT_FAILURE


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


def optimize_bind_addition(
        new: BoundFile,
        bound_files: Iterable[BoundFile]) -> Iterable[BoundFile]:
    """
    Adds new to bound_files, if needed. Performs optimizations to prevent
    double binds/superfluous binds, and returns the optimized bind set
    """

    new_binds = set(bound_files)

    def contains(bound_lhs, bound_rhs):
        try:
            return bound_rhs.origin.relative_to(
                bound_lhs.origin) == bound_rhs.destination.relative_to(
                    bound_lhs.destination)
        except ValueError:
            return False

    # Check if the file to be bound is contained in already bound files/folders
    # If it is, check that the containing files/folders' permissions align with
    # the new file and update them if need be
    target_contained = set(filter(lambda b: contains(b, new), bound_files))

    if target_contained:
        # Compute the max permission required by the files containing new. If
        # they allow a lower level of permissions, re-bind them with the
        # necessary permissions
        target_contained_permissions = max(
            map(lambda x: x.option, target_contained))

        if target_contained_permissions < new.option:
            # Re create all the binds
            new_contained = set(
                map(lambda x: BoundFile(x.origin, x.destination, new.option),
                    target_contained))

            # Remove the old binds
            new_binds = new_binds - target_contained

            # Add the ones created above
            new_binds = new_binds | new_contained

        return new_binds

    # Check if the file to be bound is containing already bound files/folders
    # If it is, check that the new file's permissions align with the contained files/folders
    # and then unbind them with a new permission level if need be
    target_containing = set(filter(lambda b: contains(new, b), bound_files))

    if target_containing:
        # Check the permissions requires by the files contained by new, and
        # update new's permissions accordingly
        target_containing_permissions = max(
            map(lambda x: x.option, target_containing))

        if target_containing_permissions > new.option:
            new = BoundFile(new.origin, new.destination,
                            target_containing_permissions)

    new_binds.add(new)
    return new_binds - target_containing


def _unrelative(string: str) -> Iterable[Path]:
    """
    Returns a list of all the directories referenced by a relative path
    """

    path = Path(string)
    visited = {path, path.resolve()}
    deps = set()

    for i, part in enumerate(path.parts):
        if part == '..':
            visited.add(Path(*path.parts[:i]).resolve())

    for element in visited:
        contained = False
        for path in visited:
            if path != element and path_contains(path, element):
                contained = True

        if not contained:
            deps.add(element)

    return deps


class Container:
    """
    Abstract class that auto-completes depending on the container tech
    """

    # pylint: disable=unused-argument
    def __new__(cls, image=None, name=None):
        """
        Object level creation hijacking: depending on the executable
        argument, the appropriate subclass will be returned.
        """
        module_name = BACKENDS.get(name)
        if module_name:
            module = sys.modules.get(module_name)
        else:
            raise BackendUnsupported(name)

        driver = object.__new__(module.CLASS)

        # If in debugging mode, print out the config before running
        if debug_mode():
            driver.run = dump(driver.run)
        driver.__str__ = dump(driver.__str__)

        return driver

    def __init__(self, image=None, name=None):
        """
        Common class init: this code is run in the actual sub-classes
        """

        # Container image identifier
        self.image = image

        # User-set parameters
        # Files to bind: set(BoundFile)
        self._bound_files = set()
        self.env = {}  # Environment
        self.ld_preload = []  # Files to put in LD_PRELOAD
        self.ld_lib_path = []  # Directories to put in LD_LIBRARY_PATH

        self.libc_v = Version('0.0.0')
        self.cache = {}

        if hasattr(self, '__setup__'):
            self.__setup__()

    @property
    def script(self):
        return Path(CONTAINER_SCRIPT)

    @property
    def import_dir(self):
        return Path(CONTAINER_DIR)

    @property
    def import_library_dir(self):
        return Path(CONTAINER_LIBRARY_DIR)

    @property
    def import_binary_dir(self):
        return Path(CONTAINER_BINARY_DIR)

    def get_data(self):
        """
        Run analysis commands in the container to get informations about the
        environment inside of it. The results will be used to tailor the
        library import to ensure compatibility of the shared objects.

        The entrypoint passed as an argument may contain external parameters
        (The source script being one of them)

        A library set with data about libraries listed in library_set will
        be returned
        """
        outstream = sys.stdout

        # Obfuscate stdout to access the output of the below commands
        with TemporaryFile() as buffer:
            sys.stdout = buffer

            code = self.run(['cat', '/etc/ld.so.cache'])

            if code:
                raise AnalysisError(code)

            sys.stdout.seek(0, 0)
            cache_data = sys.stdout.read()

            # Extract version info from the cache
            glib_version_string = get_generator(cache_data)
            if glib_version_string is not None:
                self.libc_v = Version(glib_version_string)
            else:
                # for older caches, grab the version from the ldconfig binary
                sys.stdout.seek(0, 0)
                sys.stdout.truncate(0)
                code = self.run(['ldconfig', '--version'])
                sys.stdout.seek(0, 0)
                glib_version = sys.stdout.read().decode()
                self.libc_v = Version(glib_version)

            LOGGER.debug("Detected container glibc version: %s", self.libc_v)

            # Extract libraries from the cache
            with NamedTemporaryFile('wb', delete=False) as cache_buffer:
                cache_buffer.write(cache_data)
                buffer_name = cache_buffer.name

            self.cache = cache_libraries(buffer_name)

        sys.stdout = outstream

        return set()

    def bind_file(self,
                  path: Union[Path, str],
                  dest: Optional[Path] = None,
                  option: int = FileOptions.READ_ONLY) -> None:
        """
        If there is no destination, handle files with relative paths.
        For instance on summit, some files are required as
        /jsm_pmix/container/../lib/../bin/file
        Although only /jsm_pmix/bin/file is required, not
        having jsm_pmix/container && lib makes it error out
        unrelative returns a list of all the paths required for such a file
        """
        if not path:
            return

        new_binds = set()
        if not dest:
            for _path in _unrelative(path):
                new_binds.add(BoundFile(_path, _path, option))
        else:
            new_binds.add(BoundFile(Path(path), Path(dest), option))

        for bind in new_binds:
            self._bound_files = optimize_bind_addition(bind, self._bound_files)

    @property
    def bound(self):
        for bound in self._bound_files:
            if bound.origin.exists() and bound.destination.is_absolute():
                yield bound
            else:
                LOGGER.warning(
                    "Attempting to bind non-existing file: %(source)s to %(dest)s",
                    {
                        'source': bound.origin,
                        'dest': bound.destination
                    })

    def bind_env_var(self, key, value):
        self.env.update({key: value})

    def add_ld_preload(self, path):
        if path not in self.ld_preload:
            self.ld_preload.append(path)

    def add_ld_library_path(self, path):
        if path not in self.ld_lib_path:
            self.ld_lib_path.append(path)

    def run(self, command):
        """
        run a command in a container.

        command         list[str]   the command line to execute

        This method must be implemented in the container module.
        It should take into account the parameters set in the object:
        - The bound files in self.bound;
        - The environment variables self.env;
        - The LD_PRELOAD self.ld_preload;
        - The LD_LIBRARY_PATH self.ld_lib_path
        and set them to be available in the created container.
        """
        raise NotImplementedError(
            f"`run` method not implemented for container module {self.__class__.__name__}"
        )

    def __str__(self):
        out = []
        out.append(f"{self.__class__.__name__} object:")
        if self.image:
            out.append(f"- image: {self.image}")
        bound_files = "\n".join([
            f"\t{v.origin} -> {v.destination} ({v.option})" for v in self.bound
        ])
        out.append(f"- bound:\n{bound_files}")
        if self.env:
            out.append(f"- env: { json.dumps(self.env, indent=2)}")
        if self.ld_preload:
            out.append(
                f"- LD_PRELOAD: {json.dumps(self.ld_preload, indent=2)}")
        if self.ld_lib_path:
            out.append(
                f"- LD_LIBRARY_PATH: {json.dumps(self.ld_lib_path, indent=2)}")
        return '\n'.join(out)


def guess_backend(path):
    suffix = Path(path).suffix

    matches = list(filter(lambda x: x[0] == suffix, MIMES))

    # If we cannot associate a unique backend to a MIME
    if len(matches) != 1:
        return None

    return matches[0][1]


def assert_module(_module) -> bool:
    """
    Assert a module defining a container class is properly structured
    """
    required = ['NAME', 'CLASS']

    for attribute in required:
        if not hasattr(_module, attribute):
            LOGGER.warning(
                "Container module '%s' is missing a required attribute: %s; skipping ...",
                _module.__name__, required)
            return False

    if getattr(_module, 'CLASS') and not getattr(_module.CLASS, 'run'):
        LOGGER.warning(
            "Container module '%s' has an incomplete module class; skipping ..."
        )

    return True


for _, _module_name, _ in walk_packages(__path__, prefix=__name__ + "."):
    import_module(_module_name)
    _module = sys.modules[_module_name]

    if not assert_module(_module):
        continue

    BACKENDS.update({
        _module.NAME: _module_name,
    })

    if not getattr(_module, 'DEBUG_BACKEND', False):
        EXPOSED_BACKENDS.append(_module.NAME)

    for mimetype in getattr(_module, 'MIMES', []):
        MIMES.append((mimetype, _module.NAME))
