import sys
from os import environ
from e4s_cl import util
from e4s_cl.error import InternalError

BACKENDS = []
SUPPORTED_MIMES = {}

class Container(object):
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

    def run(self, command):
        raise InternalError("Not implemented")

for _, module_name, _ in util.walk_packages(__path__, prefix=__name__ + "."):
    __import__(module_name)
    module = sys.modules[module_name]
    if not ('AVAILABLE' in dir(module) and module.AVAILABLE):
        # The module is incomplete or unavailable
        continue

    BACKENDS.append(module_name.split('.')[-1])

    for mime in sys.modules[module_name].MIMES:
        modules = SUPPORTED_MIMES.get(mime, [])
        modules.append(sys.modules[module_name].__name__)
        SUPPORTED_MIMES[mime] = modules

