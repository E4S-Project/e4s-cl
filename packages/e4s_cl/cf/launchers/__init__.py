"""launchers module
Entry point for supported program launchers"""

import sys
from pathlib import Path
from importlib import import_module
from os import environ
from e4s_cl.util import walk_packages
from e4s_cl.error import InternalError

LAUNCHERS = {}


class Parser(object):
    def __init__(self, arguments):
        self.arguments = arguments

    def parse(self, command):
        """
        parse_cli: list[str] -> list[str], list[str]

        Separate a command line into launcher and program.
        """
        position = 0
        known = True
        launcher = []

        launcher.append(command[position])
        position += 1

        while known and position < len(command):
            if command[position] not in self.arguments.keys():
                known = False
                break

            to_skip = self.arguments[command[position]]

            for index in range(0, to_skip + 1):
                launcher.append(command[position + index])

            position += (to_skip + 1)

        return launcher, command[position:]


def parse_cli(cmd):
    """Determine if the launcher is supported
    import its module and parse the command line"""
    script = Path(cmd[0]).name

    module_name = LAUNCHERS.get(script)

    if module_name:
        return sys.modules[module_name].PARSER.parse(cmd)
    raise NotImplementedError("Launcher %s is not supported" % script)


for _, module_name, _ in walk_packages(path=__path__, prefix=__name__ + '.'):
    import_module(name=module_name)
    for script_name in sys.modules[module_name].SCRIPT_NAMES:
        LAUNCHERS.update({script_name: module_name})
