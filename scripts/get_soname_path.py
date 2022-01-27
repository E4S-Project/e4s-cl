#!/bin/env python3

# Script that prints the given mpi's shared library version and distributor
# libmpi.so or equivalent is expected.

import os
import sys

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        __file__ = sys.executable

    here = os.path.realpath(os.path.dirname(__file__))
    os.environ['__E4S_CL_HOME__'] = os.path.join(here, '..')
    packages = os.path.join(here, '..', 'packages')
    sys.path.insert(0, packages)

    if len(sys.argv) < 2:
        print("Usage: %s <libmpi.so.x>" % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    from e4s_cl.cf.libraries.linker import resolve

    print(resolve(sys.argv[1]))
