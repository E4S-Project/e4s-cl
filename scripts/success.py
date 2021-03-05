#!/bin/env python3

import os
import sys

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        __file__ = sys.executable

    here = os.path.realpath(os.path.dirname(__file__))
    os.environ['__E4S_CL_HOME__'] = os.path.join(here, '..')
    packages = os.path.join(here, '..', 'packages')
    sys.path.insert(0, packages)

    from e4s_cl import logger

    logger.get_logger(__name__).warning(sys.argv[1])
