import e4s_cl
from dataclasses import dataclass
import yaml
from pathlib import Path
from os.path import expanduser, exists

user_home = expanduser('~')
default_config_path = user_home + "/.config/e4s-cl.yaml"
alternate_config_path = "/etc/e4s-cl/e4s-cl.yaml"
configuration_file = ""


def flatten(data):
    SEPARATOR = '_'
    flat = dict()

    for key in data.keys():
        value = data.get(key)
        if isinstance(value, str):
            flat.update({str(key): value})
        elif isinstance(value, dict):
            for value_key in value:
                flat.update({
                    SEPARATOR.join((str(key), str(value_key))):
                    value.get(value_key)
                })
    return flat


@dataclass(frozen=True)
class ConfigurationField:
    key: str
    expected_type: type
    default: callable


ALLOWED_CONFIG = list(
    map(lambda x: ConfigurationField(*x),
        [('container_directory', str, lambda: e4s_cl.CONTAINER_DIR),
         ('launcher_options', list, lambda: []),
         ('singularity_cli_options', list, lambda: []),
         ('preload_root_libraries', bool, lambda: False)]))


class Configuration:

    @classmethod
    def create_from(cls, config_file, complete=False):
        config = cls()

        data = {}
        if config_file and Path(config_file).exists():
            with open(config_file) as f:
                data = flatten(yaml.safe_load(f))

        field = {}
        for parameter in ALLOWED_CONFIG:
            if parameter.key in data:
                field = {parameter.key: data[parameter.key]}
            elif complete:
                field = {parameter.key: parameter.default()}

            config._fields.update(field)

        return config

    @classmethod
    @property
    def default(cls):
        return cls.create_from('', complete=True)

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
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(self)}' and '{type(rhs)}'"
            )

        return Configuration(self._fields | rhs._fields)


CONFIGURATION = Configuration.default | Configuration.create_from(
    alternate_config_path) | Configuration.create_from(default_config_path)
