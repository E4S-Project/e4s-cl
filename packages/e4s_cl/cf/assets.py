import os
import json
from pathlib import Path
from e4s_cl import USER_PREFIX, SYSTEM_PREFIX, logger

LOGGER = logger.get_logger(__name__)

BINARY_DIR = os.path.join(USER_PREFIX, 'compiled_binaries')


def _load_index(index: Path) -> dict:
    if not index.exists():
        return {}

    data = {}

    with open(index.as_posix(), 'r') as index_file:
        try:
            data = json.load(index_file)
        except json.JSONDecodeError as err:
            LOGGER.debug("Error loading index: %s", err)

    return data


def binaries() -> dict:
    user_binaries = Path(USER_PREFIX, "binaries", "index.json")
    system_binaries = Path(SYSTEM_PREFIX, "binaries", "index.json")

    available = _load_index(user_binaries) | _load_index(system_binaries)

    binaries = {}
    for soname, location in available.items():
        binaries[soname] = Path(location)

    return binaries
