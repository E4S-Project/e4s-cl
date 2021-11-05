#!/bin/env python3

import os
import stat
import sys
import lzma
import json
import requests
from pathlib import Path

here = os.path.realpath(os.path.dirname(__file__))
os.environ['__E4S_CL_HOME__'] = os.path.join(here, '..')
packages = os.path.join(here, '..', 'packages')
sys.path.insert(0, packages)

from e4s_cl import logger, USER_PREFIX

LOGGER = logger.get_logger(__name__)

BINARY_DIR = Path(USER_PREFIX, "binaries").as_posix()
PROFILE_DIR = Path(USER_PREFIX, "profiles").as_posix()
BINARY_INDEX = Path(BINARY_DIR, "index.json").as_posix()
PROFILE_INDEX = Path(PROFILE_DIR, "index.json").as_posix()


def init_dirs():
    os.makedirs(BINARY_DIR, exist_ok=True)
    os.makedirs(PROFILE_DIR, exist_ok=True)


def secure_binaries(url, available):
    """
    From a dict of {soname, suffix.xz} download and uncompress from the provided URL
    """
    downloaded = {}

    for library, binary in available.items():
        bin_url = f"{url}/{binary}"
        destination = Path(BINARY_DIR, Path(binary).stem).as_posix()

        r = requests.get(bin_url)

        if not r.ok:
            LOGGER.warn(f"Failed to access {bin_url}")
            continue

        with open(destination, "wb") as decompressed:
            xz = lzma.LZMADecompressor()

            for chunk in r.iter_content(chunk_size=8192):
                decompressed.write(xz.decompress(chunk))

        st = os.stat(destination)
        os.chmod(destination, st.st_mode | stat.S_IEXEC)

        downloaded[library] = destination

    with open(BINARY_INDEX, "w") as index_json:
        json.dump(downloaded, index_json)


def secure_profiles(url, available):
    """
    If a profile url is returned, download and put its JSON file in the profile directory
    """
    if not available:
        return

    profile_url = f"{url}/{available}"
    destination = Path(PROFILE_DIR, Path(available).name).as_posix()
    r = requests.get(profile_url)

    if not r.ok:
        LOGGER.warn(f"Failed to access {bin_url}")
        return

    with open(destination, "w") as profile:
        json.dump(r.json(), profile)


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        __file__ = sys.executable

    if len(sys.argv) < 3:
        LOGGER.error("Usage: %s <URL> <architecture> [system]", sys.argv[0])
        sys.exit(1)

    init_dirs()

    url, architecture = sys.argv[1:3]
    system = ''
    if len(sys.argv) > 3:
        system = sys.argv[3]

    index = requests.get(f"{url}/index.json")

    if not index.ok:
        LOGGER.error("Failed to download data from %s. Is the URL correct ?",
                     url)

    available = index.json()

    secure_binaries(url, available.get('binaries', {}).get(architecture, {}))
    secure_profiles(url, available.get('profiles', {}).get(system, ""))
