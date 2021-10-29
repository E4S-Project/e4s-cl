import re
from e4s_cl import logger
from functools import lru_cache
from e4s_cl.util import create_subprocess_exp

LOGGER = logger.get_logger(__name__)


class Module:
    def __init__(self, string: str):
        self.name = None
        self.version = None
        self.default = bool(re.match(r'.*(default)', string))

        components = string.split('/')

        self.name = components[0]

        if len(components) != 1:
            self.version = components[1].replace('(default)', '')

    def __repr__(self) -> str:
        string = str(self.name)

        if self.version:
            string = "%s/%s" % (string, str(self.version))

        return string

    def __str__(self) -> str:
        return repr(self)

    def __hash__(self):
        return hash(repr(self))


#def __available() -> set(Module):
@lru_cache
def __available():
    status, modules = create_subprocess_exp(['bash', '-c', 'module -t avail'],
                                            redirect_stdout=True)

    avail = set()

    if status:
        LOGGER.debug("Failed accessing available modules")
        return avail

    for line in filter(lambda x: ':' not in x, modules.split('\n')):
        avail.add(Module(line))

    return avail


#def __loaded() -> set(Module):
@lru_cache
def __loaded():
    status, modules = create_subprocess_exp(['bash', '-c', 'module -t list'],
                                            redirect_stdout=True)

    loaded = set()

    if status:
        LOGGER.debug("Failed accessing loaded modules")
        return loaded

    for line in filter(lambda x: ':' not in x, modules.split('\n')):
        loaded.add(Module(line))

    return loaded
