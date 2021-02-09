#!/bin/env python3

# lsof clone

import os
import sys
import json

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Usage: %s <command>" % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    if getattr(sys, 'frozen', False):
        __file__ = sys.executable

    here = os.path.realpath(os.path.dirname(__file__))
    os.environ['__E4S_CL_HOME__'] = os.path.join(here, '..')
    packages = os.path.join(here, '..', 'packages')
    sys.path.insert(0, packages)

    from e4s_cl.util import opened_files, which
    from e4s_cl.cf.libraries import ldd
    from e4s_cl.cli.commands.profile.detect import filter_files

    returncode, accessed_files = opened_files(sys.argv[1:])
    base_command = which(sys.argv[1])
    if base_command:
        ldd_requirements = ldd(base_command)
    libs, files = filter_files(accessed_files, ldd_requirements)

    if not returncode:
        try:
            with open("filesof.%s" % os.getpid(), "w") as f:
                json.dump({"files": files, "libraries": libs}, f, indent=2)
        except OSError:
            json.dump({"files": files, "libraries": libs}, sys.stdout)

