"""launchers module
Entry point for supported program launchers"""

import sys
from os import environ
from e4s_cl.util import walk_packages
from e4s_cl.error import InternalError

LAUNCHERS = []

for _, module_name, _ in walk_packages(__path__, prefix=""):
    LAUNCHERS.append(module_name)


def parse_cli(cmd):
    """Determine if the launcher is supported
    import its module and parse the command line"""
    module = "{}.{}".format(__name__, cmd[0])
    __import__(module)
    return sys.modules[module].parse_cli(cmd)
