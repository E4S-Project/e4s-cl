#!/bin/env python3

import os
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

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        __file__ = sys.executable

    if len(sys.argv) < 3:
        LOGGER.error("Usage: %s <URL> <architecture>", sys.argv[0])
        sys.exit(1)

    url, architecture = sys.argv[1:3]

    index = requests.get(f"{url}/index.json")

    if not index.ok:
        LOGGER.error("Failed to download data from %s. Is the URL correct ?", url)

    available = index.json()
    downloaded = {}

    for library, binary in available.get('binaries', {}).get(architecture, {}).items():
        bin_url = f"{url}/{binary}"
        destination = f"{USER_PREFIX}/binaries/{Path(binary).stem}"

        r = requests.get(bin_url)

        if not r.ok:
            LOGGER.warn(f"Failed to access {bin_url}")
            continue

        with open(destination, "wb") as decompressed:
            xz = lzma.LZMADecompressor()

            for chunk in r.iter_content(chunk_size=8192):
                decompressed.write(xz.decompress(chunk))

        downloaded[library] = destination

    binary_index = f"{USER_PREFIX}/binaries/index.json"
    with open(binary_index, "w") as index_json:
        json.dump(downloaded, index_json)
