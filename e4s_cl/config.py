"""
Load and propagate the contents of configuration files in YAML format
"""

import sys
from dataclasses import dataclass
from pathlib import Path
import yaml
import e4s_cl


def flatten(data):
    """
    Transform nested dictionaries into key value pairs by prefixing the
    parent's key, under the assumption that all keys are str.
    >>> flatten({'root': {'key1': 0, 'key2': 'test'} })
    """
    separator = '_'

    def _pre(prefix, string):
        return str(separator.join(filter(None, [prefix, string])))

    def _intermediate(prefix, data: dict):
        flat = {}

        if not data:
            return flat

        for key, value in data.items():
            if isinstance(value, dict):
                for ckey, cval in _intermediate(str(key), value).items():
                    flat.update({_pre(prefix, ckey): cval})
            else:
                flat.update({_pre(prefix, key): value})

        return flat

    return _intermediate('', data)


@dataclass(frozen=True)
class ConfigurationField:
    key: str
    expected_type: type
    default: callable


class ConfigurationError(Exception):
    """
    Do not pass through logger nor error as those depend on configuration
    """

    def handle(self, _etype, _value, _tb):
        print(self.args[0], file=sys.stderr)
        return e4s_cl.EXIT_FAILURE


class Configuration:
    """
    Class of objects abstracting configuration values. Can be created using a
    dict or class methods to complete it with defined configuration fields,
    then merged with other Configuration objects using the bitwise or operation.
    """

    @classmethod
    def create_from_string(cls, string, complete=False):
        """
        Create a Configuration object from a YAML string, with type checking.
        Will complete with default values for missing fields if complete is set
        to True.
        """

        config = cls()
        data = flatten(yaml.safe_load(string)) or {}

        for parameter in ALLOWED_CONFIG:
            field = {}
            if parameter.key in data:
                value = data[parameter.key]

                if isinstance(value, parameter.expected_type):
                    field = {parameter.key: value}
                else:
                    raise ConfigurationError(
                        f"Invalid value for parameter '{parameter.key}':"
                        f"{value} (expected {str(parameter.expected_type)})")

            elif complete:
                field = {parameter.key: parameter.default()}

            config._fields.update(field)

        return config

    @classmethod
    def create_from_file(cls, config_file, complete=False):
        yaml_contents = ''
        if config_file and Path(config_file).exists():
            with open(config_file, encoding='utf-8') as file:
                yaml_contents = file.read()

        return Configuration.create_from_string(yaml_contents,
                                                complete=complete)

    @classmethod
    def default(cls):
        return cls.create_from_string('', complete=True)

    def __init__(self, defaults=None):
        if isinstance(defaults, dict):
            self._fields = defaults
        else:
            self._fields = {}

    def __getattr__(self, identifier):
        if identifier in self._fields:
            return self._fields[identifier]
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{identifier}'"
        )

    def __or__(self, rhs):
        if not isinstance(rhs, Configuration):
            raise TypeError(f"unsupported operand type(s) for |: "
                            f"'{type(self)}' and '{type(rhs)}'")

        # Merge the two dictionaries (Use | on py39)
        return Configuration({**self._fields, **rhs._fields})


DEFAULT_CONFIG_PATH = Path.home() / ".config/e4s-cl.yaml"
ALTERNATE_CONFIG_PATH = "/etc/e4s-cl/e4s-cl.yaml"

ALLOWED_CONFIG = list(
    map(lambda x: ConfigurationField(*x),
        [('container_directory', str, lambda: e4s_cl.CONTAINER_DIR),
         ('launcher_options', list, lambda: []),
         ('singularity_cli_options', list, lambda: []),
         ('preload_root_libraries', bool, lambda: False),
         ('disable_ranked_log', bool, lambda: False)]))

CONFIGURATION = Configuration.default()
if not e4s_cl.E4S_CL_TEST:
    CONFIGURATION = CONFIGURATION  \
        | Configuration.create_from_file(ALTERNATE_CONFIG_PATH) \
        | Configuration.create_from_file(DEFAULT_CONFIG_PATH)
