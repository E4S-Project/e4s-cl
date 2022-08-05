"""
This modules parses data in the asset dirs to list all assets available during execution
"""
from pathlib import Path
from e4s_cl import logger
from e4s_cl.model.profile import Profile
from e4s_cl.cf.storage.levels import ORDERED_LEVELS, highest_writable_storage

LOGGER = logger.get_logger(__name__)

SAMPLE_BINARY_TABLE = "precompiled_binaries"
BUILTIN_PROFILE_TABLE = "builtin_profiles"

TARGET_STORAGE = highest_writable_storage()


def precompiled_binaries(storage=None) -> dict:
    """
    List all the precompiled binaries available
    """
    records = {}

    def _transform(record):
        return (record['soname'], record['path'])

    levels = reversed(ORDERED_LEVELS)
    if storage:
        levels = [storage]

    for level in levels:
        entries = level.search(table_name=SAMPLE_BINARY_TABLE)
        records = dict(map(_transform, entries), **records)

    return records


def builtin_profiles(storage=None) -> dict:
    """
    List all the builtin profiles available
    """
    records = {}

    def _transform(record):
        return (record['system'], record['configuration'])

    levels = reversed(ORDERED_LEVELS)
    if storage:
        levels = [storage]

    for level in levels:
        entries = level.search(table_name=BUILTIN_PROFILE_TABLE)
        records = dict(map(_transform, entries), **records)

    return records


def _import_asset(primary_key: str,
                  data: dict,
                  table_name: str,
                  storage=TARGET_STORAGE) -> bool:
    """
    Import `data` into the database.

    Args:

        primary_key: str: the key in data to use as a identifier
        data: dict[str, Any]: the data to import
        table_name: str: the table to import in, will be created if it does not exist

    Returns:

        bool: wether the import was successful or not
    """
    if not data.get(primary_key):
        LOGGER.error("Missing or invalid value for `%s` in asset", primary_key)
        return False

    data_id = data[primary_key]

    with storage as database:
        try:
            database.remove({primary_key: data_id}, table_name)
        except ValueError:
            return False

        # No errors according to the source, so no error checking
        database.insert(data, table_name)

    return True


def add_builtin_profile(system, configuration, storage=TARGET_STORAGE):
    """
    Record a configuration to be used as a built-in profile
    """

    check_builtin_profile(system, configuration)

    record = {
        'system': system,
        'configuration': configuration,
    }
    _import_asset('system', record, BUILTIN_PROFILE_TABLE, storage)


def check_builtin_profile(system, configuration):
    """
    Checks the downloaded profile for format validity
    """

    def check_list(path_list):
        for path in path_list:
            if not Path(path).exists():
                LOGGER.warning(
                    "Builtin profile %s has a non-existent"
                    " %s path: %s!", system, key, path)

    def check_string(path):
        if not Path(path).exists():
            LOGGER.warning(
                "Builtin profile %s has a non-existent"
                " %s path: %s!", system, key, path)

    profile_types = {'string': str, 'list': list}

    profile_paths = {
        'files': check_list,
        'libraries': check_list,
        'wi4mpi': check_string,
        'source': check_string
    }

    # Checks if the profile is a dict
    if not isinstance(configuration, dict):
        raise ValueError(f"Profile {system} data is not a dictionary!"
                         " Profile import cancelled.")

    attr = Profile.attributes
    for key in configuration:
        key_values = configuration[key]
        # Checks if the keys are correct
        if key not in attr:
            raise ValueError(
                f"Profile {system}'s keys don't match with"
                f" e4s-cl's profiles keys: '{key}' not an authorised key!"
                " Profile import cancelled.")
        key_type = profile_types.get(attr[key]['type'])
        # Checks if the values are of the correct type
        if not isinstance(key_values, key_type):
            raise ValueError(f"Profile {system} has values of the wrong"
                             f" type: '{type(key_values)}', and don't match"
                             f" with e4s-cl's {key}'s type: '{key_type}'!"
                             " Profile import cancelled.")
        # Checks if the path values point to an existing file
        if key in profile_paths:
            profile_paths.get(key)(key_values)


def remove_builtin_profile(system, storage=TARGET_STORAGE):
    """
    Remove a configuration used as a built-in profile
    """
    with storage as database:
        database.remove({'system': system})


def add_precompiled_binary(soname, path, storage=TARGET_STORAGE):
    """
    Record a path towards a precompiled MPI binary
    """
    record = {
        'soname': soname,
        'path': path,
    }
    _import_asset('soname', record, SAMPLE_BINARY_TABLE, storage)
