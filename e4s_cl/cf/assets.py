"""
This modules parses data in the asset dirs to list all assets available during execution
"""

from e4s_cl import logger
from e4s_cl.cf.storage.levels import USER_STORAGE

LOGGER = logger.get_logger(__name__)

SAMPLE_BINARY_TABLE = "precompiled_binaries"
BUILTIN_PROFILE_TABLE = "builtin_profiles"


def precompiled_binaries(storage=USER_STORAGE) -> dict:
    """
    List all the precompiled binaries available
    """
    records = storage.search(table_name=SAMPLE_BINARY_TABLE)
    transform = lambda r: (r['soname'], r['path'])

    return dict(map(transform, records))


def builtin_profiles(storage=USER_STORAGE) -> dict:
    """
    List all the builtin profiles available
    """
    records = storage.search(table_name=BUILTIN_PROFILE_TABLE)
    transform = lambda r: (r['system'], r['configuration'])

    return dict(map(transform, records))


def _import_asset(primary_key: str,
                  data: dict,
                  table_name: str,
                  storage=USER_STORAGE) -> bool:
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
        except ValueError as err:
            return False

        # No errors according to the source, so no error checking
        record = database.insert(data, table_name)

    return True


def add_builtin_profile(system, configuration, storage=USER_STORAGE):
    """
    Record a configuration to be used as a built-in profile
    """
    record = {
        'system': system,
        'configuration': configuration,
    }
    _import_asset('system', record, BUILTIN_PROFILE_TABLE, storage)


def remove_builtin_profile(system, storage=USER_STORAGE):
    """
    Remove a configuration used as a built-in profile
    """
    with storage as database:
        database.remove({'system': system})


def add_precompiled_binary(soname, path, storage=USER_STORAGE):
    """
    Record a path towards a precompiled MPI binary
    """
    record = {
        'soname': soname,
        'path': path,
    }
    _import_asset('soname', record, SAMPLE_BINARY_TABLE, storage)
