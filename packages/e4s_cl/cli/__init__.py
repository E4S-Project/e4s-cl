import os
import sys
from types import ModuleType
from e4s_cl import E4S_CL_SCRIPT, EXIT_FAILURE
from e4s_cl import logger, util
from e4s_cl.error import ConfigurationError, InternalError

LOGGER = logger.get_logger(__name__)

SCRIPT_COMMAND = os.path.basename(E4S_CL_SCRIPT)

COMMANDS_PACKAGE_NAME = __name__ + '.commands'

USAGE_FORMAT = "console"
"""Specify usage formatting:
    console: colorized and formatted to fit current console dimensions.
    markdown: plain text markdown. 
    path: list available commands from the current cli.
"""

# Override if asked to print completion info
if os.environ.get('E4S_COMPLETION') is not None:
    USAGE_FORMAT = "path"

_COMMANDS = {SCRIPT_COMMAND: {}}


class UnknownCommandError(ConfigurationError):
    """Indicates that a specified command is unknown."""
    message_fmt = ("%(value)r is not a valid command.\n" "\n" "%(hints)s")


class AmbiguousCommandError(ConfigurationError):
    """Indicates that a specified partial command is ambiguous."""
    message_fmt = ("Command '%(value)s' is ambiguous.\n" "\n" "%(hints)s")

    def __init__(self, value, matches, *hints):
        parts = [
            "Did you mean `%s %s`?" % (SCRIPT_COMMAND, match)
            for match in matches
        ]
        parts.append("Try `%s --help`" % SCRIPT_COMMAND)
        super(AmbiguousCommandError, self).__init__(value,
                                                    *hints + tuple(parts))


def _command_as_list(module_name):
    """Converts a module name to a command name list.
    
    Maps command module names to their command line equivilants, e.g.
    'e4s_cl.cli.commands.target.create' => ['tau', 'target', 'create']

    Args:
        module_name (str): Name of a module.

    Returns:
        list: Strings that identify the command.
    """
    parts = module_name.split('.')
    for part in COMMANDS_PACKAGE_NAME.split('.'):
        if parts[0] == part:
            parts = parts[1:]
    return [SCRIPT_COMMAND] + parts


def _get_commands(package_name):
    # pylint: disable=line-too-long
    """Returns a dictionary mapping commands to Python modules.
    
    Given a root module name, return a dictionary that maps commands and their
    subcommands to Python modules.  The special key ``__module__`` maps to the
    command module.  Other strings map to subcommands of the command.
    
    Args:
        package_name (str): A string naming the module to search for cli.
    
    Returns:
        dict: Strings mapping to dictionaries or modules.
        
    Example:
    ::

        _get_commands('e4s_cl.cli.commands.target') ==>
            {'__module__': <module 'e4s_cl.cli.commands.target' from '/home/jlinford/workspace/e4s_cl/packages/e4s_cl/cli/commands/target/__init__.pyc'>,
             'create': {'__module__': <module 'e4s_cl.cli.commands.target.create' from '/home/jlinford/workspace/e4s_cl/packages/e4s_cl/cli/commands/target/create.pyc'>},
             'delete': {'__module__': <module 'e4s_cl.cli.commands.target.delete' from '/home/jlinford/workspace/e4s_cl/packages/e4s_cl/cli/commands/target/delete.pyc'>},
             'edit': {'__module__': <module 'e4s_cl.cli.commands.target.edit' from '/home/jlinford/workspace/e4s_cl/packages/e4s_cl/cli/commands/target/edit.pyc'>},
             'list': {'__module__': <module 'e4s_cl.cli.commands.target.list' from '/home/jlinford/workspace/e4s_cl/packages/e4s_cl/cli/commands/target/list.pyc'>}}
    """
    def lookup(cmd, dct):
        if not cmd:
            return dct
        if len(cmd) == 1:
            return dct[cmd[0]]

        return lookup(cmd[1:], dct[cmd[0]])

    def walking_import(module, cmd, dct):
        car, cdr = cmd[0], cmd[1:]
        if cdr:
            walking_import(module, cdr, dct[car])
        elif car not in dct:
            __import__(module)
            dct.setdefault(car, {})['__module__'] = sys.modules[module]

    __import__(COMMANDS_PACKAGE_NAME)
    command_module = sys.modules[COMMANDS_PACKAGE_NAME]
    for _, module, _ in util.walk_packages(command_module.__path__,
                                           prefix=command_module.__name__ +
                                           '.'):
        if not (module.endswith('__main__') or '.tests' in module):
            try:
                lookup(_command_as_list(module), _COMMANDS)
            except KeyError:
                walking_import(module, _command_as_list(module), _COMMANDS)
    return lookup(_command_as_list(package_name), _COMMANDS)


def command_from_module_name(module_name):
    """Converts a module name to a command name string.
    
    Maps command module names to their command line equivilants, e.g.
    'e4s_cl.cli.commands.profile.show' => 'e4s-cl profile show'
    
    Args:
        module_name (str): Name of a module.
        
    Returns:
        str: A string that identifies the command.
    """
    if module_name == '__main__':
        return os.path.basename(E4S_CL_SCRIPT)

    return ' '.join(_command_as_list(module_name))


def commands_next(package_name=COMMANDS_PACKAGE_NAME):
    commands = sorted([
        i for i in _get_commands(package_name).items() if i[0] != '__module__'
    ])
    return [cmd for cmd, _ in commands]


def commands_description(package_name=COMMANDS_PACKAGE_NAME):
    """Builds listing of command names with short description.
    
    Args:
        package_name (str): A dot-seperated string naming the module to search for cli.
    
    Returns:
        str: Help string describing all commands found at or below `root`.
    """
    usage_fmt = USAGE_FORMAT.lower()
    groups = {}
    commands = sorted([
        i for i in _get_commands(package_name).items() if i[0] != '__module__'
    ])
    for cmd, topcmd in commands:
        module = topcmd['__module__']
        try:
            command_obj = module.COMMAND
        except AttributeError:
            continue
        descr = command_obj.summary.split('\n')[0]
        group = command_obj.group
        if usage_fmt == 'console':
            line = '  %s%s' % (util.color_text('{:<14}'.format(cmd),
                                               'green'), descr)
        elif usage_fmt == 'markdown':
            line = '  %s | %s' % ('{:<28}'.format(cmd), descr)
        else:
            line = ''
        groups.setdefault(group, []).append(line)
    parts = []
    for group, members in groups.items():
        title = group.title() + ' Subcommands' if group else 'Subcommands'
        if usage_fmt == 'console':
            parts.append(util.color_text(title + ':', attrs=['bold']))
        elif usage_fmt == 'markdown':
            parts.extend([
                '', ' ', '{:<30}'.format(title) + ' | Description',
                '%s:| %s' % ('-' * 30, '-' * len('Description'))
            ])
        parts.extend(members)
        parts.append('')
    return '\n'.join(parts)


def get_all_commands(package_name=COMMANDS_PACKAGE_NAME):
    """Builds a list of all commands and subcommands.

    Args:
        package_name (str): A dot-separated string naming the module to search for cli.

    Returns:
        list: List of modules corresponding to all commands and subcommands.
    """
    all_commands = []
    commands = sorted((i for i in _get_commands(package_name).items()
                       if i[0] != '__module__'))
    for _, topcmd in commands:
        for _, mod in topcmd.items():
            if isinstance(mod, dict):
                all_commands.append(mod['__module__'].__name__)
            elif isinstance(mod, ModuleType):
                all_commands.append(mod.__name__)
            else:
                raise InternalError("%s is an invalid module." % mod)
    return all_commands


def _resolve(cmd, c, d):
    # pylint: disable=invalid-name
    if not c:
        return []
    car, cdr = c[0], c[1:]
    try:
        matches = [(car, d[car])]
    except KeyError:
        matches = [i for i in d.items() if i[0].startswith(car)]
    if len(matches) == 1:
        return [matches[0][0]] + _resolve(cmd, cdr, matches[0][1])
    if len(matches) == 0:
        raise UnknownCommandError(' '.join(cmd))
    if len(matches) > 1:
        raise AmbiguousCommandError(' '.join(cmd), [m[0] for m in matches])


def find_command(cmd):
    """Import the command module and return its COMMAND member.
    
    Args:
        cmd (list): List of strings identifying the command, i.e. from :any:`_command_as_list`.
        
    Raises:
        UnknownCommandError: `cmd` is invalid.
        AmbiguousCommandError: `cmd` is ambiguous.
        
    Returns:
        AbstractCommand: Command object for the subcommand.
    """
    if cmd:
        root = '.'.join([COMMANDS_PACKAGE_NAME] + cmd)
    else:
        root = COMMANDS_PACKAGE_NAME
    try:
        return _get_commands(root)['__module__'].COMMAND
    except KeyError:
        LOGGER.debug('%r not recognized as a command', cmd)
        resolved = _resolve(cmd, cmd, _COMMANDS[SCRIPT_COMMAND])
        LOGGER.debug('Resolved ambiguous command %r to %r', cmd, resolved)
        return find_command(resolved)
    except AttributeError:
        raise InternalError("'COMMAND' undefined in %r" % cmd)


def _permute(cmd, cmd_args):
    cmd_len = len(cmd)
    full_len = len(cmd) + len(cmd_args)
    skip = [x[0] == '-' or os.path.isfile(x) for x in (cmd + cmd_args)]
    yield cmd, cmd_args
    for i in range(full_len):
        if skip[i]:
            continue
        for j in range(i + 1, full_len):
            if skip[j]:
                continue
            perm = cmd + cmd_args
            perm[i], perm[j] = perm[j], perm[i]
            yield perm[:cmd_len], perm[cmd_len:]


def execute_command(cmd, cmd_args=None, parent_module=None):
    """Import the command module and run its main routine.
    
    Partial commands are allowed, e.g. cmd=['tau', 'cli', 'commands', 'app', 'cre'] will resolve
    to 'e4s_cl.cli.commands.application.create'.  If the command can't be found then the parent 
    command (if any) will be invoked with the ``--help`` flag.
    
    Args:
        cmd (list): List of strings identifying the command, i.e. from :any:`_command_as_list`.
        cmd_args (list): Command line arguments to be parsed by command.
        parent_module (str): Dot-seperated name of the command's parent.
        
    Raises:
        UnknownCommandError: `cmd` is invalid.
        AmbiguousCommandError: `cmd` is ambiguous.
        
    Returns:
        int: Command return code.
    """
    if cmd_args is None:
        cmd_args = []

    if parent_module:
        parent = _command_as_list(parent_module)[1:]
        cmd = parent + cmd

    main = find_command(cmd).main
    return main(cmd_args)

    if len(cmd) <= 1:
        # We finally give up
        LOGGER.debug("Unknown command %r has no parent module: giving up.",
                     cmd)
        raise UnknownCommandError(' '.join(cmd))
    if not parent_module:
        parent = cmd[:-1]
    LOGGER.debug('Getting help from parent command %r', parent)
    parent_usage = util.uncolor_text(find_command(parent).usage)
    LOGGER.error("Invalid %s subcommand: %s\n\n%s", parent[0], cmd[-1],
                 parent_usage)
    return EXIT_FAILURE
