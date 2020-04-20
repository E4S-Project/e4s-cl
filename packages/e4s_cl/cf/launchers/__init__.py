import sys
from os import environ
from e4s_cl import util
from e4s_cl.error import InternalError

LAUNCHERS = []

for _, module_name, _ in util.walk_packages(__path__, prefix=""):
    LAUNCHERS.append(module_name)

def parse_cli(cmd):
    module = "{}.{}".format(__name__, cmd[0])
    __import__(module)
    return sys.modules[module].parse_cli(cmd)
