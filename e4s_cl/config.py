#pylint: disable=E1131
"""
Load and propagate the contents of configuration files in YAML format
"""

import sys
import yaml
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
from e4s_cl import (
    CONTAINER_DIR,
    E4S_CL_HOME,
    E4S_CL_TEST,
    EXIT_FAILURE,
)


def update_configuration(configuration):
    global CONFIGURATION
    CONFIGURATION = configuration


def flatten(data):
    """
    Transform nested dictionaries into key value pairs by prefixing the
    parent's key, under the assumption that all keys are str.
    >>> flatten({'root': {'key1': 0, 'key2': 'test'} })

    => dict(root_key1=0, root_key2='test')
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
    description: str = ""


@dataclass(frozen=True)
class ConfigurationGroup:
    key: str
    fields: frozenset  # [ConfigurationField|ConfigurationGroup]
    description: str = ""

    def __init__(self, key, fields, description=""):
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "fields", frozenset(fields))
        object.__setattr__(self, "description", description)

    def flatten(self):
        _fields = []

        for field in self.fields:
            if isinstance(field, ConfigurationGroup):
                _fields.extend(field.flatten())
            elif isinstance(field, ConfigurationField):
                _fields.append(field)

        for field in _fields:
            namespaced = "_".join(filter(None, [self.key, field.key]))
            yield ConfigurationField(namespaced, field.expected_type,
                                     field.default)

    def as_dict(self) -> Dict:
        out = {}

        for field in self.fields:
            if isinstance(field, ConfigurationGroup):
                out[field.key] = field.as_dict()

            elif isinstance(field, ConfigurationField):
                out[field.key] = field.default()

        return out

    def template(self):
        return yaml.safe_dump(self.as_dict())


class ConfigurationError(Exception):
    """
    Do not pass through logger nor error as those depend on configuration
    """

    def handle(self, _etype, _value, _tb):
        print(self.args[0], file=sys.stderr)
        return EXIT_FAILURE


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

        for parameter in ALLOWED_CONFIG.flatten():
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
        """
        Merge configuration objects
        The right hand side has priority, and its keys will take precedence
        """
        if not isinstance(rhs, Configuration):
            raise TypeError(f"unsupported operand type(s) for |: "
                            f"'{type(self)}' and '{type(rhs)}'")

        # Merge the two dictionaries (Use | on py39)
        return Configuration({**self._fields, **rhs._fields})

    def __str__(self):
        return str(self._fields)


USER_CONFIG_PATH = Path.home() / ".config/e4s-cl.yaml"
INSTALL_CONFIG_PATH = Path(E4S_CL_HOME) / "e4s-cl.yaml"
SYSTEM_CONFIG_PATH = "/etc/e4s-cl/e4s-cl.yaml"

ALLOWED_CONFIG = ConfigurationGroup(
    "", {
        ConfigurationField(
            "container_directory",
            str,
            lambda: CONTAINER_DIR,
            "e4s-cl data directory location inside the container",
        ),
        ConfigurationField(
            "launcher_options",
            list,
            lambda: [],
            "Additional options to pass to the process launcher",
        ),
        ConfigurationField(
            "profile_list_columns",
            list,
            lambda: [],
            "Columns to display with the profile list command",
        ),
        ConfigurationField(
            "preload_root_libraries",
            bool,
            lambda: False,
            "Insert LD_PRELOAD calls to ensure bound libraries are preloaded. Required when using RPATH'ed libraries",
        ),
        ConfigurationField(
            "disable_ranked_log",
            bool,
            lambda: False,
            "Disable logging on the work nodes",
        ),
        ConfigurationGroup(
            "backends", {
                ConfigurationGroup(
                    "singularity",
                    {
                        ConfigurationField(
                            "executable",
                            str,
                            lambda: "",
                            "Location of the singularity executable to use",
                        ),
                        ConfigurationField(
                            "options",
                            list,
                            lambda: [],
                            "Options to pass to the singularity executable",
                        ),
                        ConfigurationField(
                            "exec_options",
                            list,
                            lambda: [],
                            "Options to pass to the singularity exec command",
                        ),
                    },
                    "Singularity container backend configuration",
                ),
                ConfigurationGroup(
                    "apptainer",
                    {
                        ConfigurationField(
                            "executable",
                            str,
                            lambda: "",
                            "Location of the apptainer executable to use",
                        ),
                        ConfigurationField(
                            "options",
                            list,
                            lambda: [],
                            "Options to pass to the apptainer executable",
                        ),
                        ConfigurationField(
                            "exec_options",
                            list,
                            lambda: [],
                            "Options to pass to the apptainer exec command",
                        ),
                    },
                    "Apptainer container backend configuration",
                ),
                ConfigurationGroup(
                    "podman", {
                        ConfigurationField(
                            "executable",
                            str,
                            lambda: "",
                            "Location of the podman executable to use",
                        ),
                        ConfigurationField(
                            "options",
                            list,
                            lambda: [],
                            "Options to pass to the podman executable",
                        ),
                        ConfigurationField(
                            "run_options",
                            list,
                            lambda: [],
                            "Options to pass to the podman run command",
                        ),
                    }),
                ConfigurationGroup(
                    "shifter", {
                        ConfigurationField(
                            "executable",
                            str,
                            lambda: "",
                            "Location of the shifter executable to use",
                        ),
                        ConfigurationField(
                            "options",
                            list,
                            lambda: [],
                            "Options to pass to the shifter executable",
                        ),
                    }),
            }),
    })

CONFIGURATION = Configuration.default()
if not E4S_CL_TEST:
    CONFIGURATION = CONFIGURATION  \
        | Configuration.create_from_file(SYSTEM_CONFIG_PATH) \
        | Configuration.create_from_file(INSTALL_CONFIG_PATH) \
        | Configuration.create_from_file(USER_CONFIG_PATH)
