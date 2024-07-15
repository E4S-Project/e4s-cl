"""
Command stubs, inherited from taucmdr
"""

import re
import json
from texttable import Texttable
from e4s_cl import EXIT_SUCCESS
from e4s_cl import logger, util, cli
from e4s_cl.error import UniqueAttributeError, InternalError, ModelError
from e4s_cl.cf.storage import StorageError
from e4s_cl.cf.storage.levels import SYSTEM_STORAGE, USER_STORAGE
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand


class AbstractCliView(AbstractCommand):
    """A command that works as a `view` for a `controller`.
    
    See http://en.wikipedia.org/wiki/Model-view-controller
    
    Attributes:
        controller (class): The controller class for this view's data.
        model_name (str): The lower-case name of the model.
    """

    # pylint: disable=abstract-method

    def __init__(self,
                 model,
                 module_name,
                 summary_fmt=None,
                 help_page_fmt=None,
                 group=None,
                 include_storage_flag=True):
        self.model = model
        self.model_name = self.model.name.lower()
        format_fields = {'model_name': self.model_name}
        if not summary_fmt:
            summary_fmt = "Create and manage %(model_name)s configurations."
        self.include_storage_flag = include_storage_flag
        super().__init__(module_name,
                         format_fields=format_fields,
                         summary_fmt=summary_fmt,
                         help_page_fmt=help_page_fmt,
                         group=group)


class RootCommand(AbstractCliView):
    """A command with subcommands for actions."""

    def _construct_parser(self):
        usage = f"{self.command} <subcommand> [arguments]"
        epilog = [
            '',
            cli.commands_description(self.module_name), '',
            f"See `{self.command} <subcommand> --help` for more information on a subcommand."
        ]
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary,
                                      epilog='\n'.join(epilog))
        parser.add_argument('subcommand',
                            help="See 'subcommands' below",
                            choices=cli.commands_next(self.module_name),
                            metavar='<subcommand>')
        parser.add_argument('options',
                            help="Arguments to be passed to <subcommand>",
                            metavar='[arguments]',
                            nargs=arguments.REMAINDER)
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        return cli.execute_command([args.subcommand], args.options,
                                   self.module_name)


class CreateCommand(AbstractCliView):
    """Base class for the `create` command of command line views."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt',
                          "Create %(model_name)s configurations.")
        super().__init__(*args, **kwargs)

    def _construct_parser(self):
        usage = f"{self.command} <{self.model_name}_{self.model.key_attribute}> [arguments]"
        parser = arguments.get_parser_from_model(self.model,
                                                 prog=self.command,
                                                 usage=usage,
                                                 description=self.summary)
        if self.include_storage_flag:
            arguments.add_storage_flag(parser, "create", self.model_name)
        return parser

    def _create_record(self, store, data):
        """Create the model record.
        
        Args:
            store (AbstractStorage): Storage to contain the record.
            data (dict): Record data.
            
        Returns:
            int: :any:`EXIT_SUCCESS` if successful.
        
        Raises:
            UniqueAttributeError: A record with the same unique attribute already exists.
        """
        ctrl = self.model.controller(store)
        key_attr = self.model.key_attribute
        key = data[key_attr]
        try:
            ctrl.create(data)
        except UniqueAttributeError:
            self.parser.error(
                f"A {self.model_name} with {key_attr}='{key}' already exists")
        return EXIT_SUCCESS

    def main(self, argv):
        args = self._parse_args(argv)
        store = arguments.parse_storage_flag(args)[0]
        data = {
            attr: getattr(args, attr)
            for attr in self.model.attributes if hasattr(args, attr)
        }
        return self._create_record(store, data)


class DeleteCommand(AbstractCliView):
    """Base class for the `delete` subcommand of command line views."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt',
                          "Delete %(model_name)s configurations.")
        super().__init__(*args, **kwargs)

    def _construct_parser(self):
        key_attr = self.model.key_attribute
        usage = f"{self.command} <{self.model_name}_{key_attr}> [arguments]"
        epilog = util.color_text("WARNING: THIS OPERATION IS NOT REVERSABLE!",
                                 'yellow',
                                 attrs=['bold'])
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary,
                                      epilog=epilog)
        parser.add_argument(
            key_attr,
            help=
            f"{key_attr.capitalize()} of {self.model_name} configuration to delete",
            nargs="+",
            type=arguments.wildcard_defined_object(self.model, key_attr),
            metavar=f"<{self.model_name}_{key_attr}>")
        if self.include_storage_flag:
            arguments.add_storage_flag(parser, "delete", self.model_name)
        return parser

    def _delete_record(self, store, obj):
        key_attr = self.model.key_attribute
        key = obj.get(key_attr)
        ctrl = self.model.controller(store)
        if not ctrl.exists({key_attr: key}):
            self.parser.error(
                f"No {store.name}-level {self.model_name} with {key_attr}='{key}'."
            )
        ctrl.delete({key_attr: key})
        self.logger.info("Deleted %s '%s'", self.model_name, key)
        return EXIT_SUCCESS

    def main(self, argv):
        args = self._parse_args(argv)
        store = arguments.parse_storage_flag(args)[0]
        objects = getattr(args, self.model.key_attribute)
        for obj in objects:
            for elem in obj:
                self._delete_record(store, elem)
        return EXIT_SUCCESS


class EditCommand(AbstractCliView):
    """Base class for the `edit` subcommand of command line views."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt',
                          "Modify %(model_name)s configurations.")
        self.include_new_key_flag = kwargs.pop('include_new_key_flag', True)
        super().__init__(*args, **kwargs)

    def _construct_parser(self):
        key_attr = self.model.key_attribute
        usage = f"{self.command} <{self.model_name}_{key_attr}> [arguments]"
        parser = arguments.get_parser_from_model(self.model,
                                                 use_defaults=False,
                                                 prog=self.command,
                                                 usage=usage,
                                                 description=self.summary)
        if self.include_new_key_flag:
            group = parser.add_argument_group(f'{self.model_name} arguments')
            group.add_argument(f"--new-{key_attr}",
                               help=f"change the configuration's {key_attr}",
                               metavar=f"<new_{key_attr}>",
                               dest='new_key',
                               default=arguments.SUPPRESS)
        if self.include_storage_flag:
            arguments.add_storage_flag(parser, "modify", self.model_name)
        return parser

    def _update_record(self, store, data, key):
        ctrl = self.model.controller(store)
        key_attr = self.model.key_attribute
        if not ctrl.exists({key_attr: key}):
            self.parser.error(
                f"No {ctrl.storage.name}-level {self.model_name} with {key_attr}='{key}'."
            )
        ctrl.update(data, {key_attr: key})
        self.logger.info("Updated %s '%s'", self.model_name, key)
        return EXIT_SUCCESS

    def main(self, argv):
        args = self._parse_args(argv)
        store = arguments.parse_storage_flag(args)[0]
        data = {
            attr: getattr(args, attr)
            for attr in self.model.attributes if hasattr(args, attr)
        }
        key_attr = self.model.key_attribute
        try:
            data[key_attr] = args.new_key
        except AttributeError:
            pass
        key = getattr(args, key_attr)
        return self._update_record(store, data, key)


class ListCommand(AbstractCliView):
    """Base class for the `list` subcommand of command line views."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt',
                          "Show %(model_name)s configuration data.")
        default_style = kwargs.pop('default_style', 'dashboard')
        dashboard_columns = kwargs.pop('dashboard_columns', None)
        title_fmt = kwargs.pop(
            'title_fmt', "%(model_name)s Configurations (%(storage_path)s)")
        super().__init__(*args, **kwargs)
        key_attr = self.model.key_attribute
        self._format_fields = {
            'command': self.command,
            'model_name': self.model_name,
            'key_attr': key_attr
        }
        self.default_style = default_style
        self.dashboard_columns = dashboard_columns or [{
            'header':
            key_attr.title(),
            'value':
            key_attr
        }]
        self.title_fmt = title_fmt

    def short_format(self, models):
        """Format modeled records in short format.

        Args:
            models: Modeled records to format.

        Returns:
            str: Record data in short format.
        """
        return [str(model[self.model.key_attribute]) for model in models]

    def dashboard_format(self, records):
        """Format modeled records in dashboard format.

        Args:
            records: Modeled records to format.
 
        Returns:
            str: Record data in dashboard format.
        """
        title = util.hline(
            self.title_fmt % {
                'model_name': records[0].name.capitalize(),
                'storage_path': records[0].storage
            }, 'cyan')
        header_row = [col['header'] for col in self.dashboard_columns]
        rows = [header_row]
        for record in records:
            row = []
            for col in self.dashboard_columns:
                if 'value' in col:
                    try:
                        cell = record[col['value']]
                    except KeyError:
                        cell = 'N/A'
                elif 'yesno' in col:
                    cell = 'Yes' if record.get(col['yesno'], False) else 'No'
                elif 'function' in col:
                    cell = col['function'](record)
                else:
                    raise InternalError(f"Invalid column definition: {col}")
                row.append(cell)
            rows.append(row)
        table = Texttable(logger.LINE_WIDTH)
        table.set_cols_align(
            [col.get('align', 'c') for col in self.dashboard_columns])
        table.add_rows(rows)
        return [title, table.draw(), '']

    def _format_long_item(self, key, val):
        attrs = self.model.attributes[key]
        if 'collection' in attrs:
            foreign_model = attrs['collection']
            foreign_keys = []
            for foreign_record in val:
                try:
                    foreign_keys.append(
                        str(foreign_record[foreign_model.key_attribute]))
                except (AttributeError, ModelError):
                    foreign_keys.append(str(foreign_record))
            val = ', '.join(foreign_keys)
        elif 'model' in attrs:
            foreign_model = attrs['model']
            try:
                val = str(val[foreign_model.key_attribute])
            except (AttributeError, ModelError):
                val = str(val)
        elif 'type' in attrs:
            if attrs['type'] == 'boolean':
                val = str(bool(val))
            elif attrs['type'] == 'array':
                val = ', '.join(str(x) for x in val)
            elif attrs['type'] != 'string':
                val = str(val)
        else:
            raise InternalError(f"Attribute has no type: {attrs}, {val}")
        description = attrs.get('description', 'No description')
        description = description[0].upper() + description[1:] + "."
        return [key, val, description]

    def long_format(self, records):
        """Format records in long format.
        
        Args:
            records: Controlled records to format.
        
        Returns:
            str: Record data in long format.
        """
        title = util.hline(
            self.title_fmt % {
                'model_name': records[0].name.capitalize(),
                'storage_path': records[0].storage
            }, 'cyan')
        retval = [title]
        for record in records:
            rows = [['Attribute', 'Value', 'Description']]
            for key, val in sorted(record.items()):
                if key != self.model.key_attribute:
                    rows.append(self._format_long_item(key, val))
            table = Texttable(logger.LINE_WIDTH)
            table.set_cols_align(['r', 'c', 'l'])
            table.set_deco(Texttable.HEADER | Texttable.VLINES)
            table.add_rows(rows)
            retval.append(util.hline(record[self.model.key_attribute], 'cyan'))
            retval.extend([table.draw(), ''])
        return retval

    def _construct_parser(self):
        key_str = self.model_name + '_' + self.model.key_attribute
        usage_head = (
            f"{self.command} [{key_str}] [{key_str}] ... [arguments]")
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage_head,
                                      description=self.summary)
        parser.add_argument(
            'keys',
            help=("Show only %(model_name)ss with the given %(key_attr)ss" %
                  self._format_fields),
            metavar=key_str,
            nargs='*',
            default=arguments.SUPPRESS)
        style_dest = 'style'
        style_group = parser.add_mutually_exclusive_group()
        style_group.add_argument('-s',
                                 '--short',
                                 help="show minimal %(model_name)s data" %
                                 self._format_fields,
                                 const='short',
                                 action='store_const',
                                 dest=style_dest,
                                 default=arguments.SUPPRESS)
        style_group.add_argument(
            '-d',
            '--dashboard',
            help="show %(model_name)s data in a fancy dasboard" %
            self._format_fields,
            const='dashboard',
            action='store_const',
            dest=style_dest,
            default=arguments.SUPPRESS)
        style_group.add_argument(
            '-l',
            '--long',
            help="show all %(model_name)s data in a list" %
            self._format_fields,
            const='long',
            action='store_const',
            dest=style_dest,
            default=arguments.SUPPRESS)
        if self.include_storage_flag:
            arguments.add_storage_flag(parser,
                                       "show",
                                       self.model_name,
                                       plural=True,
                                       exclusive=False)
        return parser

    def _list_records(self, storage_levels, keys, style):
        """Shows record data via `print`.
        
        Args:
            storage_levels (list): Storage levels to query, e.g. ['user', 'profile']
            keys (list): Keys to match to :any:`self.key_attr`.
            style (str): Style in which to format records.
            
        Returns:
            int: :any:`EXIT_SUCCESS` if successful.
        """
        user_ctl = self.model.controller(USER_STORAGE)
        system_ctl = self.model.controller(SYSTEM_STORAGE)

        system = SYSTEM_STORAGE.name in storage_levels
        user = USER_STORAGE.name in storage_levels

        parts = []
        if system:
            parts.extend(self._format_records(system_ctl, style, keys))
        if user:
            parts.extend(self._format_records(user_ctl, style, keys))
        if style == 'dashboard':
            # Show record counts (not the records themselves) for other storage levels
            if not system:
                parts.extend(self._count_records(system_ctl))
            if not user:
                parts.extend(self._count_records(user_ctl))
        print("\n".join(parts))
        return EXIT_SUCCESS

    def main(self, argv):
        args = self._parse_args(argv)
        keys = getattr(args, 'keys', None)
        style = getattr(args, 'style', None) or self.default_style
        storage_levels = [l.name for l in arguments.parse_storage_flag(args)]
        return self._list_records(storage_levels, keys, style)

    def _retrieve_records(self, ctrl, keys):
        """Retrieve modeled data from the controller.
        
        Args:
            ctrl (Controller): Controller for the data model.
            keys (list): Keys to match to :any:`self.key_attr`.
            
        Returns:
            list: Model records.
        """
        if not keys:
            records = ctrl.all()
        else:
            key_attr = self.model.key_attribute
            matches = [
                ctrl.match(key_attr, regex=f"^{re.escape(key)}.*")
                for key in keys
            ]

            for i, record in enumerate(matches):
                if not record:
                    self.parser.error(
                        f"No {self.model_name} with {key_attr} matching '{keys[i]}'"
                    )

            records = list(set(util.flatten(matches)))

        return records

    def _format_records(self, ctrl, style, keys=None):
        """Format records in a given style.
        
        Retrieves records for controller `ctrl` and formats them.
        
        Args:
            ctrl (Controller): Controller for the data model.
            style (str): Style in which to format records.        
            keys (list): Keys to match to :any:`self.key_attr`.
            
        Returns:
            list: Record data as formatted strings.
        """
        try:
            records = self._retrieve_records(ctrl, keys)
        except StorageError:
            records = []
        if not records:
            parts = [f"No {self.model_name}s."]
        else:
            formatter = getattr(self, style + '_format')
            parts = formatter(records)
        return parts

    def _count_records(self, ctrl):
        """Print a record count to stdout.
        
        Args:
            controller (Controller): Controller for the data model.
        """
        level = ctrl.storage.name
        try:
            count = ctrl.count()
        except StorageError:
            count = 0
        fields = dict(self._format_fields,
                      count=count,
                      level=level,
                      level_flag=arguments.STORAGE_LEVEL_FLAG)
        if count == 1:
            return [
                "There is 1 %(level)s %(model_name)s."
                " Type `%(command)s -%(level_flag)s %(level)s` to list it." %
                fields
            ]
        if count > 1:
            return [
                "There are %(count)d %(level)s %(model_name)ss."
                " Type `%(command)s -%(level_flag)s %(level)s` to list them." %
                fields
            ]
        #return ["There are no %(level)s %(model_name)ss." % fields]
        return []


class DumpCommand(AbstractCliView):
    """
    Dump json data from the database
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt',
                          "Dump %(model_name)s configuration data.")
        super().__init__(*args, **kwargs)
        key_attr = self.model.key_attribute
        self._format_fields = {
            'command': self.command,
            'model_name': self.model_name,
            'key_attr': key_attr
        }

    def _construct_parser(self):
        key_str = self.model_name + '_' + self.model.key_attribute
        usage_head = (
            "%(command)s [%(key_str)s] [%(key_str)s] ... [arguments]" % {
                'command': self.command,
                'key_str': key_str
            })
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage_head,
                                      description=self.summary)
        parser.add_argument(
            'keys',
            help=(
                "Dump only the %(model_name)ss with the given %(key_attr)ss" %
                self._format_fields),
            metavar=key_str,
            nargs='*',
            default=arguments.SUPPRESS)
        if self.include_storage_flag:
            arguments.add_storage_flag(parser,
                                       "show",
                                       self.model_name,
                                       plural=True,
                                       exclusive=False)
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        keys = getattr(args, 'keys', None)
        storage_levels = [l.name for l in arguments.parse_storage_flag(args)]
        return self._dump_records(storage_levels, keys)

    def _retrieve_records(self, ctrl, keys):
        """Retrieve modeled data from the controller.
        
        Args:
            ctrl (Controller): Controller for the data model.
            keys (list): Keys to match to :any:`self.key_attr`.
            
        Returns:
            list: Model records.
        """
        if not keys:
            records = ctrl.all()
        else:
            key_attr = self.model.key_attribute
            if len(keys) == 1:
                records = ctrl.search({key_attr: keys[0]})
                if not records:
                    self.parser.error(
                        f"No {self.model_name} with {key_attr} '{keys[0]}'")
            else:
                records = ctrl.search([{key_attr: key} for key in keys])
                for i, record in enumerate(records):
                    if not record:
                        self.parser.error(
                            f"No {self.model_name} with {key_attr} '{keys[i]}'"
                        )
        return records

    def _dump_records(self, storage_levels, keys):
        """Shows record data via `print`.
        
        Args:
            storage_levels (list): Storage levels to query, e.g. ['user', 'profile']
            keys (list): Keys to match to :any:`self.key_attr`.
            
        Returns:
            int: :any:`EXIT_SUCCESS` if successful.
        """
        user_ctl = self.model.controller(USER_STORAGE)
        system_ctl = self.model.controller(SYSTEM_STORAGE)

        system = SYSTEM_STORAGE.name in storage_levels
        user = USER_STORAGE.name in storage_levels

        parts = []
        if system:
            try:
                parts += self._retrieve_records(system_ctl, keys)
            except StorageError:
                pass

        if user:
            try:
                parts += self._retrieve_records(user_ctl, keys)
            except StorageError:
                pass

        print(json.dumps(parts))

        return EXIT_SUCCESS


class ShowCommand(AbstractCliView):
    """
    Print details on an object
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt',
                          "Show %(model_name)s configuration data.")
        super().__init__(*args, **kwargs)
        self._format_fields = {
            'command': self.command,
            'model_name': self.model_name,
            'key_attr': self.model.key_attribute
        }

    def _construct_parser(self):
        usage = ("%(command)s [arguments] <%(model_name)s_%(key_attr)s>" %
                 self._format_fields)
        parser = arguments.get_model_identifier(self.model,
                                                prog=self.command,
                                                usage=usage,
                                                description=self.summary)
        return parser

    def main(self, argv):
        return EXIT_SUCCESS


class CopyCommand(CreateCommand):
    """Base class for the `copy` subcommand of command line views."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt', "Copy %(model_name)s.")
        super().__init__(*args, **kwargs)

    def _construct_parser(self):
        key_attr = self.model.key_attribute
        usage = f"{self.command} <{self.model_name}_{key_attr}> <copy_{key_attr}> [arguments]"
        parser = arguments.get_model_identifier(self.model,
                                                prog=self.command,
                                                usage=usage,
                                                description=self.summary)
        group = parser.add_argument_group(f'{self.model_name} arguments')
        group.add_argument(
            f'copy_{key_attr}',
            help=f"new {self.model_name} configuration's {key_attr}",
            metavar=f'<copy_{key_attr}>',
            default=arguments.SUPPRESS)
        if self.include_storage_flag:
            arguments.add_storage_flag(parser, "copy", self.model_name)
        return parser

    def _copy_record(self, store, updates, key):
        ctrl = self.model.controller(store)
        key_attr = self.model.key_attribute
        matching = ctrl.search({key_attr: key})
        found = []
        if not matching:
            self.parser.error(
                f"No {ctrl.storage.name}-level {self.model_name} with {key_attr}='{key}'."
            )
        elif len(matching) > 1:
            raise InternalError(
                f"More than one {ctrl.storage.name}-level {self.model_name} with {key_attr}='{key}' exists!"
            )
        else:
            found = matching[0]
        data = dict(found)
        data.update(updates)
        return self._create_record(store, data)

    def main(self, argv):
        args = self._parse_args(argv)
        store = arguments.parse_storage_flag(args)[0]
        _object = getattr(args, self.model.name.lower())
        data = {
            attr: getattr(args, attr)
            for attr in self.model.attributes if hasattr(args, attr)
        }
        key_attr = self.model.key_attribute
        try:
            data[key_attr] = getattr(args, f'copy_{key_attr}')
        except AttributeError:
            pass
        key = _object.get(key_attr)
        return self._copy_record(store, data, key)
