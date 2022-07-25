import os
import yaml
from dataclasses import dataclass
from pathlib import Path
import e4s_cl


def flatten(data):
    SEPARATOR = '_'

    def _p(prefix, string):
        return str(SEPARATOR.join(filter(None, [prefix, string])))

    def _intermediate(prefix, data: dict):
        flat = dict()

        if not data:
            return flat

        for key, value in data.items():
            if isinstance(value, dict):
                for ckey, cval in _intermediate(str(key), value).items():
                    flat.update({_p(prefix, ckey): cval})
            else:
                flat.update({_p(prefix, key): value})

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

    def handle(self, etype, value, tb):
        print(self.args[0], file=stderr)
        return EXIT_FAILURE


class Configuration:

    @classmethod
    def create_from_string(cls, string, complete=False):
        config = cls()

        data = flatten(yaml.safe_load(string)) or {}

        field = {}
        for parameter in ALLOWED_CONFIG:
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
            with open(config_file) as f:
                yaml_contents = f.read()

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

        return Configuration(self._fields | rhs._fields)


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
if not os.environ.get('__E4S_CL_TEST__'):
    CONFIGURATION = CONFIGURATION  \
        | Configuration.create_from_file(ALTERNATE_CONFIG_PATH) \
        | Configuration.create_from_file(DEFAULT_CONFIG_PATH)
