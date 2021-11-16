"""
This modules parses data in the asset dirs to list all assets available during execution
"""

import json
from pathlib import Path
from functools import lru_cache
from e4s_cl import USER_PREFIX, SYSTEM_PREFIX, logger

LOGGER = logger.get_logger(__name__)

BINARY_DIR = "binaries"
PROFILE_DIR = "profiles"


def _load_index(index: Path) -> dict:
    if not index.exists():
        return {}

    data = {}

    with open(index.as_posix(), 'r', encoding="utf8") as index_file:
        try:
            data = json.load(index_file)
        except json.JSONDecodeError as err:
            LOGGER.debug("Error loading index: %s", err)

    return data


def _get_available(asset_dir: str) -> dict:
    user_assets = Path(USER_PREFIX, asset_dir, "index.json")
    system_assets = Path(SYSTEM_PREFIX, asset_dir, "index.json")

    # User assets have priority over system's
    available = _load_index(system_assets) | _load_index(user_assets)

    assets = {}
    for id_, path_ in available.items():
        assets[id_] = Path(path_)

    return assets


@lru_cache
def binaries() -> dict:
    return _get_available(BINARY_DIR)


@lru_cache
def profiles() -> dict:
    return _get_available(PROFILE_DIR)
