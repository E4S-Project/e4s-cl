"""launchers module
Entry point for supported program launchers"""

import sys
import re
from os import environ
from typing import List, Tuple
from pathlib import Path
from importlib import import_module
from shlex import split
from e4s_cl import logger, config
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
            elif re.match(r'^--[\-A-Za-z0-9]+=.*$', flag):
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


def get_launcher(cmd: List[str]):
    """
    Return a launcher module for the given command
    """
    if not cmd or cmd is None:
        return None

    script = Path(cmd[0]).name
    module_name = LAUNCHERS.get(script)

    if not module_name:
        return None
    return sys.modules[module_name]


def get_reserved_directories(cmd: List[str]):
    launcher_module = get_launcher(cmd)
    if launcher_module is not None and getattr(launcher_module, 'META', False):
        if 'reserved_directories' in launcher_module.META:
            return list(map(Path,
                            launcher_module.META['reserved_directories']))

    return []


def parse_cli(cmd):
    """
    Parse a command line to split it into launcher and command
    """
    if not cmd:
        return [], []

    module = get_launcher(cmd)

    if module:
        return module.PARSER.parse(cmd)
    raise NotImplementedError(f"Launcher {Path(cmd[0]).name} is not supported")


def _additional_options() -> list[str]:
    marker = "launcher_options"

    env_options = environ.get(marker.upper(), None)
    if env_options:
        return split(env_options)

    config_options = getattr(
        config.CONFIGURATION,
        marker,
        None,
    )

    if config_options:
        return config_options

    return []


def interpret(cmd: List[str]) -> Tuple[List[str], List[str]]:
    """
    Parses a command line to split the launcher command and application command.
    """
    launcher_cmd = []

    # If '--' appears in the command then everything before it is a launcher + args
    # and everything after is the application + args
    if '--' in cmd:
        idx = cmd.index('--')
        launcher_cmd, cmd = cmd[:idx], cmd[idx + 1:]
    elif Path(cmd[0]).name in LAUNCHERS:
        launcher_cmd, cmd = parse_cli(cmd)

    return [*launcher_cmd, *_additional_options()], cmd


def filter_arguments(parser: Parser,
                     cmd: List[str]) -> Tuple[List[str], List[str]]:
    """Filter a list of arguments into the ones defined by the given parser
    and foreign ones, and return them in two lists"""
    valid, foreign = [], []

    tokens = list(cmd)
    while tokens:
        token = tokens.pop(0)
        if token in parser.arguments:
            to_consume = min(parser.arguments[token], len(tokens))
            valid.append(token)
            for _ in range(to_consume):
                valid.append(tokens.pop(0))
        else:
            foreign.append(token)

    return valid, foreign
