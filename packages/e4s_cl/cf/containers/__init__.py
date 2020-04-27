"""containers module

Defines an abstract class to simplify the use of container technology.
Creating an instance of ``Container`` will return a specific class to
the required backend."""

import sys
from os import environ
from e4s_cl import util
from e4s_cl.error import InternalError

BACKENDS = []
SUPPORTED_MIMES = {}

class Container():
    """Abstract class to complete depending on the container tech."""
    def __new__(cls, backend=None, image=None):
        if backend:
            module_name = "{}.{}".format(__name__, backend)
            module = sys.modules.get(module_name)
            if not module:
                raise InternalError("Backend {} not found" .format(module_name))
            return object.__new__(module.CLASS)
        raise InternalError("No backend provided")

    def __init__(self, backend=None, image=None):
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

for _, existing_backend, _ in util.walk_packages(__path__, prefix=__name__ + "."):
    __import__(existing_backend)
    backend_module = sys.modules[existing_backend]
    if not ('AVAILABLE' in dir(backend_module) and backend_module.AVAILABLE):
        # The module is incomplete or unavailable
        continue

    BACKENDS.append(existing_backend.split('.')[-1])
