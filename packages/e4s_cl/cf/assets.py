"""
This modules parses data in the asset dirs to list all assets available during execution
"""

from e4s_cl import logger
from e4s_cl.cf.storage.levels import USER_STORAGE

LOGGER = logger.get_logger(__name__)

SAMPLE_BINARY_ID = "precompiled_binaries"
BUILTIN_PROFILE_ID = "builtin_profiles"


def precompiled_binaries(storage=USER_STORAGE) -> dict:
    """
    List all the precompiled binaries available
    """
    records = storage.search(table_name=SAMPLE_BINARY_ID)
    transform = lambda r: (r['soname'], r['path'])

    return dict(map(transform, records))


def builtin_profiles(storage=USER_STORAGE) -> dict:
    """
    List all the builtin profiles available
    """
    records = storage.search(table_name=BUILTIN_PROFILE_ID)
    transform = lambda r: (r['system'], r['configuration'])

    return dict(map(transform, records))


def _import_asset(key, data, table_name, storage=USER_STORAGE):
    if key not in data.keys():
        LOGGER.error("Asset data misses the %s key", key)
        return

    with storage as database:
        if database.contains({key: data[key]}, table_name):
            database.remove({key: data[key]}, table_name)
        record = database.insert(data, table_name)

    if not record:
        LOGGER.error("Failed to import asset for %s %s in %s storage", key,
                     data[key], storage.name)


def add_builtin_profile(system, configuration, storage=USER_STORAGE):
    """
    Record a configuration to be used as a built-in profile
    """
    record = {
        'system': system,
        'configuration': configuration,
    }
    _import_asset('system', record, BUILTIN_PROFILE_ID, storage)


def add_precompiled_binary(soname, path, storage=USER_STORAGE):
    """
    Record a path towards a precompiled MPI binary
    """
    record = {
        'soname': soname,
        'path': path,
    }
    _import_asset('soname', record, SAMPLE_BINARY_ID, storage)
