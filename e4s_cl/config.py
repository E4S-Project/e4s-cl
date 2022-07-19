import e4s_cl
from dataclasses import dataclass
import yaml
from pathlib import Path
from os.path import expanduser, exists

confxGlobal = {
    'container_directory': 'CONTAINER_DIR',
    'launcher options': 'LAUNCHER_OPTIONS',
    'top level libraries preload': 'PRELOAD',
    'singularity': 'SINGULARITY_OPTIONS'
}

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
         ('singularity_cli_options', list, lambda: [])]))


class Configuration:

    def __init__(self, confFile):
        self._fields = {}

        data = {}
        if confFile and Path(confFile).exists():
            with open(confFile) as f:
                data = flatten(yaml.safe_load(f))

        for parameter in ALLOWED_CONFIG:
            if parameter.key in data:
                field = {parameter.key: data[parameter.key]}
            else:
                field = {parameter.key: parameter.default()}

            self._fields.update(field)

    def __getattr__(self, identifier):
        if identifier in self._fields:
            return self._fields[identifier]
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{identifier}'"
        )


if exists(default_config_path):
    configuration_file = default_config_path
elif exists(alternate_config_path):
    configuration_file = alternate_config_path

CONFIGURATION_VALUES = None

if CONFIGURATION_VALUES is None and configuration_file:
    CONFIGURATION_VALUES = Configuration(configuration_file).raw_data

configuration = Configuration(configuration_file)
