import yaml
from os.path import expanduser, exists

confxGlobal = {
    'container directory': 'CONTAINER_DIR',
    'launcher options': 'LAUNCHER_OPTIONS',
    'top level libraries preload': 'PRELOAD',
    'singularity': 'SINGULARITY_OPTIONS'
}

user_home = expanduser('~')
default_config_path = user_home + "/.config/e4s-cl.yaml"
alternate_config_path = "/etc/e4s-cl/e4s-cl.yaml"
configuration_file = ""


def flatten(data):
    flat = dict()
    for key in data.keys():
        value = data.get(key)
        if isinstance(value, str):
            flat.update({str(key): value})
        elif isinstance(value, dict):
            for value_key in value:
                flat.update({
                    '.'.join((str(key), str(value_key))):
                    value.get(value_key)
                })
    return flat


@dataclass(frozen=True)
class ConfigurationField:
    key: str
    expected_type: type
    default: callable


ALLOWED_CONFIG = list(
    map(lambda x: ConfigurationField(*x), [
        ('container dir', str, lambda: e4s_cl.CONTAINER_DIR),
        ('launcher options', list, lambda: []),
    ]))


class Configuration:
    raw_data = dict()

    def __init__(self, confFile):
        if confFile:
            with open(confFile) as f:
                self.data = yaml.safe_load(f)
            for key in self.data.keys():
                self.raw_data.update({confxGlobal[key]: self.data[key]})

    def options(self, option, sub_option=None):
        if self.raw_data and self.raw_data.get(option):
            value = self.raw_data.get(option)
            if isinstance(value, bool):
                return value
            elif isinstance(value, dict):
                return value.get(sub_option).split()
            return value.split()
        return []


if exists(default_config_path):
    configuration_file = default_config_path
elif exists(alternate_config_path):
    configuration_file = alternate_config_path

CONFIGURATION_VALUES = None

if CONFIGURATION_VALUES is None and configuration_file:
    CONFIGURATION_VALUES = Configuration(configuration_file).raw_data

configuration = Configuration(configuration_file)
