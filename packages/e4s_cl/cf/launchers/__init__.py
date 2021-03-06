"""launchers module
Entry point for supported program launchers"""

import sys
import re
from pathlib import Path
from importlib import import_module
from os import environ
from e4s_cl import logger
from e4s_cl.util import walk_packages
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)


class Parser:
    """
    Default parser.

    Relies on a dictionnary, arguments, with an almost-exhaustive list
    of the launchers options to determine when the launcher stops and
    when the command begins.

    All the --option=value will be caught and don't need to be present in
    the dictionnary.

    A minimal launcher module can use this to simplify implementation:
    ```
    from e4s_cl.cf.launchers import Parser
    SCRIPT_NAMES = [identifiers]
    ARGUMENTS = {...}
    PARSER = Parser(ARGUMENTS)
    ```
    """
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
            flag = command[position]

            if flag in self.arguments.keys():
                to_skip = self.arguments[flag]

            # Catch generic --flag=value
            elif re.match(r'^--[\-A-Za-z]+=.*$', flag):
                to_skip = 0

            else:
                known = False
                break

            for index in range(0, to_skip + 1):
                launcher.append(command[position + index])

            position += (to_skip + 1)

        return launcher, command[position:]


LAUNCHERS = {}

for _, _module_name, _ in walk_packages(path=__path__, prefix=__name__ + '.'):
    import_module(name=_module_name)
    for script_name in sys.modules[_module_name].SCRIPT_NAMES:
        LAUNCHERS.update({script_name: _module_name})


def parse_cli(cmd):
    """
    Determine if the launcher is supported
    import its module and parse the command line
    """
    script = Path(cmd[0]).name

    module_name = LAUNCHERS.get(script)

    if module_name:
        return sys.modules[module_name].PARSER.parse(cmd)
    raise NotImplementedError("Launcher %s is not supported" % script)


def interpret(cmd):
    """Parses a command line to split the launcher command and application commands.

       Args:
           cmd (list[str]): Command line.

       Returns:
           tuple: (Launcher command, possibly empty list of application commands).
       """
    launcher_cmd = []

    # If '--' appears in the command then everything before it is a launcher + args
    # and everything after is the application + args
    if '--' in cmd:
        idx = cmd.index('--')
        launcher_cmd, cmd = cmd[:idx], cmd[idx + 1:]
    elif Path(cmd[0]).name in LAUNCHERS:
        launcher_cmd, cmd = parse_cli(cmd)

    env_args = environ.get('E4SCL_LAUNCHER_ARGS')

    if launcher_cmd and env_args:
        launcher_cmd += env_args.split(' ')

    # No launcher command, just an application command
    return launcher_cmd, cmd
