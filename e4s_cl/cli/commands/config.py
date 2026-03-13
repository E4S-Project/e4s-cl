"""Management of the e4s-cl configuration file."""
import yaml
from pathlib import Path
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, logger
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.config import ALLOWED_CONFIG, USER_CONFIG_PATH
from e4s_cl.util import mkdirp

LOGGER = logger.get_logger(__name__)


def _update_config(config_file, key, value):
    config = {}
    if config_file and Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as config_fh:
            config = yaml.safe_load(config_fh) or {}

    flattened_key = "_".join(key.split('.'))
    allowed_keys = {f.key: f for f in ALLOWED_CONFIG.flatten()}

    if flattened_key not in allowed_keys:
        LOGGER.error(
            "Invalid configuration key '%s'. Available keys: %s",
            key, ', '.join(allowed_keys.keys()))
        return False

    field_info = allowed_keys[flattened_key]

    try:
        if field_info.expected_type is bool:
            if value.lower() in ['true', 'yes', '1']:
                cast_value = True
            elif value.lower() in ['false', 'no', '0']:
                cast_value = False
            else:
                raise ValueError("Not a boolean")
        else:
            cast_value = field_info.expected_type(value)
    except ValueError:
        LOGGER.error(
            "Invalid value '%s' for key '%s'. Expected type: %s",
            value, key, field_info.expected_type.__name__)
        return False

    def set_recursive(current_dict, key_parts, val):
        if not key_parts:
            return
        head = key_parts[0]
        if len(key_parts) == 1:
            current_dict[head] = val
        else:
            if head not in current_dict:
                current_dict[head] = {}
            if not isinstance(current_dict[head], dict):
                current_dict[head] = {}
            set_recursive(current_dict[head], key_parts[1:], val)

    def get_path_segments(group, flat_key):
        for field in group.fields:
            if hasattr(field, 'fields'):
                prefix = field.key + "_" if field.key else ""
                if flat_key.startswith(prefix):
                    suffix = flat_key[len(prefix):]
                    res = get_path_segments(field, suffix)
                    if res is not None:
                        return [field.key] + res if field.key else res
            else:
                if field.key == flat_key:
                    return [field.key]
        return None

    segments = get_path_segments(ALLOWED_CONFIG, flattened_key)

    if not segments:
        LOGGER.error("Could not resolve key '%s' to configuration structure.", key)
        return False

    set_recursive(config, segments, cast_value)

    if not mkdirp(Path(config_file).parent):
        LOGGER.error("Could not create directory for %s", config_file)
        return False

    with open(config_file, 'w', encoding='utf-8') as config_fh:
        yaml.safe_dump(config, config_fh, default_flow_style=False)

    return True


def unflatten(flat_dict):
    """Reconstruct a nested config dict from a flat keyed dict.

    For example ``'wi4mpi_install_directory'`` becomes
    ``{'wi4mpi': {'install_directory': ...}}``.  The ALLOWED_CONFIG tree is
    used to determine grouping.
    """
    nested = {}

    def set_recursive(current_dict, key_parts, val):
        if not key_parts:
            return
        head = key_parts[0]
        if len(key_parts) == 1:
            current_dict[head] = val
        else:
            if head not in current_dict:
                current_dict[head] = {}
            if not isinstance(current_dict[head], dict):  # pragma: no cover
                current_dict[head] = {}
            set_recursive(current_dict[head], key_parts[1:], val)

    key_path_map = {}

    def traverse(group, current_path):
        for field in group.fields:
            if hasattr(field, 'fields'):
                traverse(field, current_path + [field.key])
            else:
                full_path = current_path + [field.key]
                flat_key = "_".join(filter(None, full_path))
                key_path_map[flat_key] = full_path

    traverse(ALLOWED_CONFIG, [])

    for flat_key, value in flat_dict.items():
        if flat_key in key_path_map:
            path = key_path_map[flat_key]
            set_recursive(nested, path, value)
        else:
            nested[flat_key] = value

    return nested


class ConfigCommand(AbstractCommand):
    """Manage the configuration."""

    def _construct_parser(self):
        parser = arguments.get_parser(prog=self.command, description=self.summary)
        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        subparsers.add_parser('list', help='List configuration options')
        set_parser = subparsers.add_parser('set', help='Set a configuration option')
        set_parser.add_argument(
            'key',
            help='Configuration key (can use dot notation, e.g. wi4mpi.install_directory)')
        set_parser.add_argument('value', help='Value to set')
        get_parser = subparsers.add_parser('get', help='Get a configuration option value')
        get_parser.add_argument(
            'key',
            help='Configuration key (can use dot or underscore notation)')
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        if not args.action:
            print(self.parser.format_help())
            return EXIT_FAILURE

        if args.action == 'list':
            from e4s_cl.config import CONFIGURATION
            nested = unflatten(CONFIGURATION._fields)
            print(yaml.safe_dump(nested, default_flow_style=False))
            return EXIT_SUCCESS

        if args.action == 'set':
            key = args.key.replace('.', '_')
            if _update_config(USER_CONFIG_PATH, key, args.value):
                print(f"Updated {USER_CONFIG_PATH}")
                return EXIT_SUCCESS
            return EXIT_FAILURE

        if args.action == 'get':
            from e4s_cl.config import CONFIGURATION
            key = args.key.replace('.', '_')
            try:
                val = getattr(CONFIGURATION, key)
                print(val)
                return EXIT_SUCCESS
            except AttributeError:
                LOGGER.error("Key '%s' not found in configuration.", key)
                return EXIT_FAILURE

        return EXIT_SUCCESS


COMMAND = ConfigCommand(__name__, summary_fmt="Configuration management")
