from e4s_cl import SYSTEM_PREFIX, USER_PREFIX
from e4s_cl.cf.storage import StorageError
from e4s_cl.cf.storage.local_file import LocalFileStorage
from e4s_cl.cf.storage.profile import ProfileStorage

SYSTEM_STORAGE = LocalFileStorage('system', SYSTEM_PREFIX)
"""System-level data storage."""

USER_STORAGE = LocalFileStorage('user', USER_PREFIX)
"""User-level data storage."""

PROFILE_STORAGE = USER_STORAGE

ORDERED_LEVELS = (USER_STORAGE, SYSTEM_STORAGE)
"""All storage levels in their preferred order."""

STORAGE_LEVELS = {level.name: level for level in ORDERED_LEVELS}
"""All storage levels indexed by their names."""

def highest_writable_storage():
    try:
        return highest_writable_storage.value
    except AttributeError:
        for storage in reversed(ORDERED_LEVELS):
            if storage.is_writable():
                highest_writable_storage.value = storage
                break
        else:
            raise StorageError("No writable storage levels")
        return highest_writable_storage.value

