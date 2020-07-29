"""containers module

Defines an abstract class to simplify the use of container technology.
Creating an instance of ``Container`` will return a specific class to
the required backend."""

import sys
from importlib import import_module
from pathlib import Path
from e4s_cl.util import walk_packages, which
from e4s_cl.error import InternalError

EXECUTABLES = {}
MIMES = {}


class Container():
    """Abstract class to complete depending on the container tech."""

    # pylint: disable=unused-argument
    def __new__(cls, image=None, executable=None):
        module_name = EXECUTABLES.get(Path(executable).name)
        module = sys.modules.get(module_name)

        if not module_name or not module:
            raise InternalError("Backend {} not found".format(module_name))

        return object.__new__(module.CLASS)

    def __init__(self, image=None, executable=None):
        # Module's known executables
        # sys.modules[self.__module__].EXECUTABLES

        self.executable = which(executable)

        if not self.executable or (not Path(self.executable).exists()):
            raise InternalError("Executable %s not found" % executable)

        self.image = image
        self.bound = []
        self.env = {}
        self.ld_preload = []
        self.ld_lib_path = []

    def bind_file(self, path, dest=None, options=None):
        self.bound.append((path, dest, options))

    def bind_env_var(self, key, value):
        self.env.update({key: value})

    def add_ld_preload(self, path):
        self.ld_preload.append(path)

    def add_ld_library_path(self, path):
        self.ld_lib_path.append(path)

    def run(self, command, redirect_stdout=False):
        raise InternalError("Not implemented")


for _, module_name, _ in walk_packages(__path__, prefix=__name__ + "."):
    import_module(module_name)
    module = sys.modules[module_name]

    for executable in module.EXECUTABLES:
        EXECUTABLES.update({executable: module_name})

    for mimetype in module.MIMES:
        MIMES.update({mimetype: module_name})
