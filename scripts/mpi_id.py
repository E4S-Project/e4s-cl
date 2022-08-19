#!/bin/env python3

# Script that prints the given mpi's shared library version and distributor
# libmpi.so or equivalent is expected.

import os
import sys
from e4s_cl.cf.detect_name import _get_mpi_library_version

USAGE = "Usage: %s <libmpi.so.x>" % sys.argv[0]

DESCRIPTION = \
f"""{USAGE}

This program will extract and run the function associated to the 'MPI_Get_library_version' symbol from any shared object it is given.
"""

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        __file__ = sys.executable

    if len(sys.argv) < 2:
        print(DESCRIPTION, end='')
        sys.exit(1)

    print(_get_mpi_library_version(sys.argv[1]), end='')
    sys.exit(0)
