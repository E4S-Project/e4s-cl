"""launchers module
Entry point for supported program launchers"""

import re
import sys
from os import environ
from types import ModuleType
from typing import (
    Dict,
    List,
    Tuple,
    Optional,
)
from pathlib import Path
from importlib import import_module
from shlex import split
from e4s_cl import logger, config
from e4s_cl.util import (
    get_env,
    walk_packages,
)
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)


class Parser:
    """
    Default parser.

    Uses a dictionary of known options when available, but applies robust
    fallbacks so unknown options don't prematurely terminate parsing.

    Rules:
    - '--' ends option parsing; remainder is the program.
    - ':' (Open MPI app-context delimiter) is retained on the launcher side.
      Note: multi-app context still needs higher-level handling to inject the
      wrapper before each app.
    - Known options consume their declared nargs.
    - '--opt=value' is always accepted.
    - Unknown long options ('--opt') consume one value if the next token isn't
      an option; otherwise consume none.
    - Unknown short options consume one value if the next token isn't an option.
      For concatenated known 1-arg short opts (e.g., '-xFOO=bar'), the entire
      token is accepted as one.
    """

    def __init__(self, arguments: Dict[str, int]):
        self.arguments = arguments or {}

    @staticmethod
    def _is_option(tok: str) -> bool:
        return tok.startswith('-') and tok != '-'

    @staticmethod
    def _has_inline_value(tok: str) -> bool:
        return tok.startswith('--') and '=' in tok

    def parse(self, command: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separate a command line into launcher and program.
        """
        if not command:
            return [], []

        position = 0
        launcher = [command[position]]
        position += 1
        n = len(command)

        while position < n:
            flag = command[position]

            # End-of-options sentinel: keep it on the launcher side and stop
            if flag == '--':
                launcher.append(flag)
                position += 1
                break

            # Open MPI app-context delimiter: retain and continue parsing
            if flag == ':':
                launcher.append(flag)
                position += 1
                continue

            # Known option: consume declared nargs
            if flag in self.arguments:
                nargs = self.arguments[flag]
                launcher.append(flag)
                # Append up to nargs following tokens safely
                for k in range(min(nargs, n - position - 1)):
                    launcher.append(command[position + 1 + k])
                position += 1 + nargs
                continue

            # Generic '--opt=value'
            if self._has_inline_value(flag):
                launcher.append(flag)
                position += 1
                continue

            # Unknown long option: '--opt'
            if flag.startswith('--'):
                launcher.append(flag)
                # Heuristic: if next token is not an option, treat as value
                if position + 1 < n and not self._is_option(command[position + 1]):
                    launcher.append(command[position + 1])
                    position += 2
                else:
                    position += 1
                continue

            # Short options (unknown or concatenated)
            if flag.startswith('-') and flag != '-':
                # If any known 1-arg option is a prefix of this token, accept concatenated form
                concatenated = next(
                    (
                        opt for opt, nargs in self.arguments.items()
                        if nargs == 1 and flag.startswith(opt)
                    ),
                    None,
                )
                if concatenated:
                    launcher.append(flag)
                    position += 1
                    continue

                # Otherwise, assume unknown short option possibly with one value
                launcher.append(flag)
                if position + 1 < n and not self._is_option(command[position + 1]):
                    launcher.append(command[position + 1])
                    position += 2
                else:
                    position += 1
                continue

            # First non-option token: program starts here
            break

        return launcher, command[position:]

LAUNCHERS = {}

for _, _module_name, _ in walk_packages(path=__path__, prefix=__name__ + '.'):
    import_module(name=_module_name)
    for script_name in sys.modules[_module_name].SCRIPT_NAMES:
        LAUNCHERS.update({script_name: _module_name})


def get_launcher(cmd: List[str]) -> Optional[ModuleType]:
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


def get_reserved_directories(cmd: List[str]) -> List[Path]:
    launcher_module = get_launcher(cmd)
    if launcher_module is not None and getattr(launcher_module, 'META', False):
        if 'reserved_directories' in launcher_module.META:
            return list(map(Path,
                            launcher_module.META['reserved_directories']))

    return []


def _additional_options() -> List[str]:
    marker = "launcher_options"

    env_options = get_env(marker)
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
    Tries its best to understand what part of a command line is the launcher
    and what part is the application
    """
    # Assert cmd[0] is valid by terminating for empty lists
    if not cmd:
        return [], []

    def _parse_from_mod(cmd):
        module = get_launcher(cmd)

        if module is None:
            raise NotImplementedError(
                f"Launcher {Path(cmd[0]).name} is not supported")

        return module.PARSER.parse(cmd)

    # If '--' appears in the command then everything before it is a launcher + args
    # and everything after is the application + args
    if '--' in cmd:
        idx = cmd.index('--')
        launcher, application = cmd[:idx], cmd[idx + 1:]
    elif Path(cmd[0]).name in LAUNCHERS:
        launcher, application = _parse_from_mod(cmd)
    else:
        return [], cmd

    return [*launcher, *_additional_options()], application


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
