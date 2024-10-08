"""
Module home of the argument parser methods and helpers
"""

import sys
import re
import copy
import argparse
import textwrap
from pathlib import Path
from gettext import gettext as _
from operator import attrgetter
from e4s_cl import logger, util
from e4s_cl.cli import USAGE_FORMAT
from e4s_cl.util import add_dot
from e4s_cl.error import InternalError
from e4s_cl.cf.storage import StorageError
from e4s_cl.cf.storage.levels import ORDERED_LEVELS, STORAGE_LEVELS

Action = argparse.Action
"""Action base class."""

ArgumentError = argparse.ArgumentError
"""Argument error exception base class."""

ArgumentTypeError = argparse.ArgumentTypeError
"""Argument type error exception."""

ArgumentsNamespace = argparse.Namespace
"""Generic container for parsed arguments."""

SUPPRESS = argparse.SUPPRESS
"""Suppress attribute creation in parsed argument namespace."""

REMAINDER = argparse.REMAINDER
"""All the remaining command-line arguments are gathered into a list."""

UNSELECTED = "==NOT_SELECTED=="

STORAGE_LEVEL_FLAG = "@"
"""Command line flag that indicates storage level."""

_DEFAULT_STORAGE_LEVEL = ORDERED_LEVELS[0].name

LOGGER = logger.get_logger(__name__)


class MutableArgumentGroup(argparse._ArgumentGroup):
    """Argument group that allows its actions to be modified after creation."""

    # We're changing the behavior of the superclass so we need to access protected members
    # pylint: disable=protected-access

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, option_string):
        return self._option_string_actions[option_string]


class MutableArgumentGroupParser(argparse.ArgumentParser):
    """Argument parser with mutable groups and better help formatting.

    :py:class:`argparse.ArgumentParser` doesn't allow groups to change once set 
    and generates "scruffy" looking help, so we fix this problems in this subclass.
    """

    # We're changing the behavior of the superclass so we need to access protected members
    # pylint: disable=protected-access

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actions = self._actions

    def __getitem__(self, option_string):
        return self._option_string_actions[option_string]

    def exit(self, status=0, message=None):
        if status and message:
            LOGGER.error(message)
        sys.exit(status)

    def error(self, message):
        """From the sources of python 3.8:
        error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        LOGGER.error(self.format_usage())
        args = {'prog': self.prog, 'message': message}
        self.exit(2, _('%(prog)s: error: %(message)s\n') % args)

    def add_argument_group(self, *args, **kwargs):
        """Returns an argument group.
        
        If the group doesn't exist it will be created.
        
        Args:
            *args: Positional arguments to pass to :any:`ArgumentParser.add_argument_group`
            **kwargs: Keyword arguments to pass to :any:`ArgumentParser.add_argument_group`

        Returns:
            An argument group object.
        """
        title = kwargs.get('title', args[0])
        for group in self._action_groups:
            if group.title == title:
                return group
        group = MutableArgumentGroup(self, *args, **kwargs)
        self._action_groups.append(group)
        return group

    def _format_help_console(self):
        """Format command line help string."""
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)
        formatter.add_text(self.description)
        for action_group in self._sorted_groups():
            title = ' '.join(x[0].upper() + x[1:]
                             for x in action_group.title.split())
            formatter.start_section(title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(
                sorted(action_group._group_actions,
                       key=attrgetter('option_strings')))
            formatter.end_section()
        formatter.add_text(self.epilog)
        return formatter.format_help()

    def format_help(self):
        try:
            func = getattr(self, '_format_help_' + USAGE_FORMAT.lower())
        except AttributeError as attr_err:
            raise InternalError(
                f"Invalid USAGE_FORMAT: {USAGE_FORMAT}") from attr_err
        return func()

    def _sorted_groups(self):
        """Iterate over action groups."""
        positional_title = 'positional arguments'
        optional_title = 'optional arguments'
        groups = sorted(self._action_groups, key=lambda x: x.title.lower())
        for group in groups:
            if group.title == positional_title:
                yield group
                break
        for group in groups:
            if group.title == optional_title:
                yield group
                break
        for group in groups:
            if group.title not in [positional_title, optional_title]:
                yield group

    def merge(self,
              parser,
              group_title=None,
              include_positional=False,
              include_optional=True,
              include_storage=False,
              exclude_groups=None,
              exclude_arguments=None):
        """Merge arguments from a parser into this parser.
        
        Modify this parser by adding additional arguments copied from the supplied parser.
        
        Args:
            parser (MutableArgumentGroupParser): Parser to pull arguments from.
            group_title (str): Optional group title for merged arguments.
            include_positional (bool): If True, include positional arguments.
            include_optional (bool): If True, include optional arguments.
            include_storage (bool): If True, include the storage level argument, see :any:`STORAGE_LEVEL_FLAG`.
            exclude_groups (list): Strings identifying argument groups that should be excluded.
            exclude_arguments (list): Strings identifying arguments that should be excluded.
        """
        for action in parser.actions:
            if exclude_groups and action.container.title in exclude_groups:
                continue
            dst_group = self.add_argument_group(
                group_title if group_title else action.container.title)
            optional = bool(action.option_strings)
            storage = '-' + STORAGE_LEVEL_FLAG in action.option_strings
            excluded = exclude_arguments and bool([
                optstr for optstr in action.option_strings
                for substr in exclude_arguments if substr in optstr
            ])
            # pylint: disable=too-many-boolean-expressions
            if (excluded or (not include_storage and storage)
                    or (not include_optional and optional)
                    or (not include_positional and not optional)):
                continue
            try:
                dst_group._add_action(copy.copy(action))
            except argparse.ArgumentError:
                # Argument is already in this parser.
                pass


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help string formatter for argument parser.
    
    Provide proper help message alignment, line width, and formatting.
    Uses console line width (:any:`logger.LINE_WIDTH`) to format help 
    messages appropriately so they don't wrap in strange ways.
    
    Args:
        prog (str): Name of the program.
        indent_increment (int): Number of spaces to indent wrapped lines.
        max_help_position (int): Column on which to begin subsequent lines of wrapped help strings.
        width (int): Maximum help message length before wrapping.
    """

    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=30,
                 width=None):
        if width is None:
            width = logger.LINE_WIDTH
        super().__init__(prog, indent_increment, max_help_position, width)

    def _split_lines(self, text, width):
        parts = []
        for line in text.splitlines():
            parts.extend(textwrap.wrap(line, width))
        return parts

    def _get_help_string(self, action):
        helpstr = add_dot(action.help)
        helpstr = helpstr[0].upper() + helpstr[1:]
        # Disabled in favour of per-help customization
        # indent = ' ' * self._indent_increment
        # if choices := getattr(action, 'choices', None)
        # helpstr += '\n%s- %s: %s' % (indent, action.metavar,
        # ', '.join(choices))
        # if '%(default)' not in action.help:
        # if action.default is not argparse.SUPPRESS:
        # defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
        # if action.option_strings or action.nargs in defaulting_nargs:
        # if isinstance(action.default, list):
        # default_str = ', '.join(action.default)
        # else:
        # default_str = str(action.default)
        #helpstr += '\n%s' % indent + '- default: %s' % default_str
        return helpstr

    def _format_positional(self, argstr):
        return argstr

    def _format_optional(self, argstr):
        return argstr

    def _format_requred_arg(self, argstr):
        return argstr

    def _format_optional_arg(self, argstr):
        return argstr

    def _format_meta_arg(self, argstr):
        return argstr

    def _format_args(self, action, default_metavar):
        # pylint: disable=consider-using-f-string
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = self._format_requred_arg('%s' % get_metavar(1))
        elif action.nargs == argparse.OPTIONAL:
            result = self._format_optional_arg('[%s]' % get_metavar(1))
        elif action.nargs == argparse.ZERO_OR_MORE:
            result = self._format_optional_arg('[%s [%s ...]]' %
                                               get_metavar(2))
        elif action.nargs == argparse.ONE_OR_MORE:
            tpl = get_metavar(2)
            result = self._format_requred_arg(
                '%s' % tpl[0]) + self._format_optional_arg(
                    ' [%s ...]' % tpl[1])
        elif action.nargs == argparse.REMAINDER:
            result = self._format_requred_arg('...')
        elif action.nargs == argparse.PARSER:
            result = self._format_requred_arg('%s ...' % get_metavar(1))
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return self._format_positional(metavar)

        parts = []
        if action.nargs == 0:
            parts.extend(
                self._format_optional(x) for x in action.option_strings)
        else:
            default = action.dest.upper()
            args_string = self._format_args(action, default)
            for option_string in action.option_strings:
                parts.append(
                    f'{self._format_optional(option_string)} {args_string}')
        return ', '.join(parts)


class ConsoleHelpFormatter(HelpFormatter):
    """Custom help string formatter for console output."""

    def start_section(self, heading):
        return super().start_section(util.color_text(heading, attrs=['bold']))

    def add_argument(self, action):
        if action.help is not SUPPRESS:
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            for subaction in self._iter_indented_subactions(action):
                invocations.append(get_invocation(subaction))
            invocation_length = max(
                len(util.uncolor_text(s)) for s in invocations)
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length,
                                          action_length)
            self._add_item(self._format_action, [action])

    def _format_positional(self, argstr):
        return util.color_text(argstr, 'red')

    def _format_optional(self, argstr):
        return util.color_text(argstr, 'red')

    def _format_requred_arg(self, argstr):
        return util.color_text(argstr, 'blue')

    def _format_optional_arg(self, argstr):
        return util.color_text(argstr, 'cyan')

    def _format_action(self, action):
        # pylint: disable=consider-using-f-string
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)
        action_header_nocolor = util.uncolor_text(action_header)
        if not action.help:
            # No help; start on same line and add a final newline
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
        elif len(action_header_nocolor) <= action_width:
            # Short action name; start on the same line and pad two spaces
            # Adjust length to account for color control chars
            length = action_width + len(action_header) - len(
                action_header_nocolor)
            tup = self._current_indent, '', length, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0
        else:
            # Long action name; start on the next line
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position
        parts = [action_header]
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            parts.append('%*s%s\n' % (indent_first, '', help_lines[0])) # pylint: disable=E0606
            for line in help_lines[1:]:
                parts.append('%*s%s\n' % (help_position, '', line))
        elif not action_header.endswith('\n'):
            parts.append('\n')
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))
        return self._join_parts(parts)


class ParseBooleanAction(argparse.Action):
    """Argument parser action for boolean values.
    
    Essentially a wrapper around :any:`e4s_cl.util.parse_bool`.
    """

    # pylint: disable=too-few-public-methods

    def __call__(self, parser, namespace, value, unused_option_string=None):
        """Sets the `self.dest` attribute in `namespace` to the parsed value of `value`.
        
        If `value` parses to a boolean via :any:`e4s_cl.util.parse_bool` then the 
        attribute value is that boolean value.
            
        Args:
            parser (str): Argument parser object this group belongs to.
            namespace (object): Namespace to receive parsed value via setattr.
            value (str): Value parsed from the command line/
        """
        try:
            setattr(namespace, self.dest, util.parse_bool(value))
        except TypeError as type_err:
            raise argparse.ArgumentError(
                self, 'Boolean value required') from type_err


def get_parser(prog=None, usage=None, description=None, epilog=None):
    """Builds an argument parser.
    
    The returned argument parser accepts no arguments.
    Use :any:`argparse.ArgumentParser.add_argument` to add arguments.
    
    Args:
        prog (str): Name of the program.
        usage (str): Description of the program's usage.
        description (str): Text to display before the argument help.
        epilog (str): Text to display after the argument help.

    Returns:
        MutableArgumentGroupParser: The customized argument parser object.
    """
    try:
        formatter = getattr(sys.modules[__name__],
                            USAGE_FORMAT.capitalize() + 'HelpFormatter')
    except AttributeError as attr_err:
        raise InternalError(
            f"Invalid USAGE_FORMAT: {USAGE_FORMAT}") from attr_err
    return MutableArgumentGroupParser(prog=prog,
                                      usage=usage,
                                      description=description,
                                      epilog=epilog,
                                      formatter_class=formatter)


def get_parser_from_model(model,
                          use_defaults=True,
                          prog=None,
                          usage=None,
                          description=None,
                          epilog=None):
    """Builds an argument parser from a model's attributes.
    
    The returned argument parser will accept arguments as defined by the model's `argparse` 
    attribute properties, where the arguments to :any:`argparse.ArgumentParser.add_argument` 
    are specified as keyword arguments.
    
    Examples:
        Given this model attribute:
        ::
        
            'openmp': {
                'type': 'boolean', 
                'description': 'application uses OpenMP',
                'default': False, 
                'argparse': {'flags': ('--openmp',),
                             'metavar': 'T/F',
                             'nargs': '?',
                             'const': True,
                             'action': ParseBooleanAction},
            }

        The returned parser will accept the ``--openmp`` flag accepting zero or one arguments 
        with 'T/F' as the metavar.  If ``--openmp`` is omitted the default value of False will
        be used.  If ``--openmp`` is provided with zero arguments, the const value of True will
        be used.  If ``--openmp`` is provided with one argument then the provided argument will
        be passed to a ParseBooleanAction instance to generate a boolean value.  The argument's
        help description will appear as "application uses OpenMP" if the ``--help`` argument is given.
    
    Args:
        model (Model): Model to construct arguments from.
        use_defaults (bool): If True, use the model attribute's default value 
                             as the argument's value if argument is not specified. 
        prog (str): Name of the program.
        usage (str): Description of the program's usage.
        description (str): Text to display before the argument help.
        epilog (str): Text to display after the argument help.

    Returns:
        MutableArgumentGroupParser: The customized argument parser object.        
    """
    parser = get_parser(prog, usage, description, epilog)
    groups = {}
    for attr, props in model.attributes.items():
        try:
            options = dict(props['argparse'])
        except KeyError:
            if 'primary_key' in props:
                options = {'metavar': f'<{model.name.lower()}_{attr}>'}
            else:
                continue
        if use_defaults:
            options['default'] = props.get('default', argparse.SUPPRESS)
        else:
            options['default'] = argparse.SUPPRESS
        try:
            options['help'] = props['description']
        except KeyError:
            pass
        try:
            group_name = options['group'] + ' arguments'
        except KeyError:
            group_name = model.name.lower() + ' arguments'
        else:
            del options['group']
        group = groups.setdefault(group_name,
                                  parser.add_argument_group(group_name))
        try:
            flags = options['flags']
        except KeyError:
            flags = (attr, )
        else:
            del options['flags']
            options['dest'] = attr
        prop_type = props.get('type', 'string')
        if prop_type == 'array':
            if 'nargs' not in options:
                options['nargs'] = '+'
        elif prop_type == 'boolean':
            if 'action' not in options:
                options['action'] = ParseBooleanAction
            if 'nargs' not in options:
                options['nargs'] = '?'
            if 'const' not in options:
                options['const'] = True
            if 'metavar' not in options:
                options['metavar'] = 'T/F'
        else:
            if 'type' not in options:
                options['type'] = {
                    'integer': int,
                    'float': float,
                    'boolean': str,
                    'string': str
                }[prop_type]
        group.add_argument(*flags, **options)
    return parser


def get_model_identifier(model,
                         prog=None,
                         usage=None,
                         description=None,
                         epilog=None):
    """
    Get a parser identifying a model from its key_attribute. If nothing is 
    specified, the model's selected() method is used as default.
    """
    parser = get_parser(prog, usage, description, epilog)

    model_name = model.name.lower()
    key_attr = model.key_attribute

    _default = SUPPRESS
    if 'selected' in dir(model):
        _default = model.selected().get(key_attr, UNSELECTED)

    parser.add_argument(
        model_name,
        nargs='?',
        type=single_defined_object(model, key_attr),
        help=
        f"The target {model_name}. If omitted, defaults to the selected {model_name}",
        default=_default,
        metavar=f"{model_name}_{key_attr}")

    return parser


def add_storage_flag(parser,
                     action,
                     object_name,
                     plural=False,
                     exclusive=True):
    """Add flag to indicate target storage container.
    
    Args:
        parser (MutableArgumentGroupParser): The parser to modify.
        action (str): The action that will be taken by the command, e.g. "delete" or "list"
        object_name (str): The type of object that will be manipulated, e.g. "application" or "measurement"
        plural (bool): Pluralize help message if True.
        exclusive (bool): Only one storage level may be specified if True.
    """
    help_parts = [
        "%s %ss" if plural else "%s the %s", " at the specified storage ",
        "level" if exclusive else "levels"
    ]
    help_str = "".join(help_parts) % (action, object_name)
    nargs = 1 if exclusive else '+'
    choices = [container.name for container in ORDERED_LEVELS]
    parser.add_argument('-' + STORAGE_LEVEL_FLAG,
                        help=help_str,
                        metavar="<level>",
                        nargs=nargs,
                        choices=choices,
                        default=[_DEFAULT_STORAGE_LEVEL])


def parse_storage_flag(args):
    try:
        names = getattr(args, STORAGE_LEVEL_FLAG)
    except AttributeError:
        names = [_DEFAULT_STORAGE_LEVEL]
    return [STORAGE_LEVELS[name] for name in names]


def posix_path(string):
    """Argument type callback.
    Returns a posix-compliant path."""
    if string:
        return Path(string.strip()).as_posix()
    return ''


def posix_path_list(string):
    """Argument type callback.
    Asserts that the string corresponds to a list of paths."""
    return list(map(posix_path, string.split(',')))


def existing_posix_path(string):
    """
    Argument type callback.
    Returns a posix-compliant path if it exists."""
    path = Path(string.strip())

    if not path.exists():
        raise argparse.ArgumentTypeError(
            f"File {path.as_posix()} does not exist")

    return path


def existing_posix_path_list(string):
    """Argument type callback.
    Asserts that the string corresponds to a list of existing paths."""
    return list(map(existing_posix_path, string.split(',')))


def binary_in_path(string):
    """ Argument type callback. Asserts the given string identifies a launcher binary
    on the system. """

    path = util.which(string)
    if not path:
        raise ArgumentTypeError(
            f"Launcher argument '{string}' could not be resolved to a binary")
    return path


def _search_available_databases(model, field, regex):
    matches = []

    for level in ORDERED_LEVELS:
        try:
            matches.extend(model.controller(storage=level).match(field, regex))
        except StorageError:
            LOGGER.debug("Failed to access records from level %s", level.name)

    return matches


def single_defined_object(model, field):
    """Argument type callback.
    Asserts that the string corresponds to an existing object."""

    def wrapper(string):
        if string == UNSELECTED:
            raise argparse.ArgumentTypeError(
                f"no {model.name} selected nor specified")

        matches = _search_available_databases(model, field,
                                              f"^{re.escape(string)}.*")
        exact_matches = list(filter(lambda x: x.get(field) == string, matches))

        # If multiple matches occur, return the first occurence
        if len(exact_matches) > 1:
            LOGGER.debug("Multiple exact %s matches for %s ! %s", field,
                         model.name.lower(), exact_matches)
            exact_matches = exact_matches[:1]

        # If there are multiple matches and no exact match
        if len(matches) != 1 and len(exact_matches) != 1:
            raise argparse.ArgumentTypeError(
                f"Pattern '{string}' does not identify a single {model.name.lower()}: "
                f"{len(matches)} {model.name.lower()}s match")

        if exact_matches:
            return exact_matches.pop()
        return matches.pop()

    wrapper.__name__ = f"defined_{model.name.lower()}"

    return wrapper


def wildcard_defined_object(model, field):
    """Argument type callback.
    Asserts that the string corresponds to an existing object."""

    def wrapper(string):
        if string == UNSELECTED:
            raise argparse.ArgumentTypeError(
                f"no {model.name} selected nor specified")

        wildcard_string = re.sub(re.escape('\#'), '.*', re.escape(string))
        matches = _search_available_databases(model, field,
                                              f"^{wildcard_string}$")

        if not matches:
            raise argparse.ArgumentTypeError(
                f"Pattern '{string}' does not identify any {model.name.lower()}: "
                f"{len(matches)} {model.name.lower()}s match")
        return matches

    wrapper.__name__ = f"defined_{model.name.lower()}"

    return wrapper
