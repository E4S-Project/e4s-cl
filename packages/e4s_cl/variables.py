import os
from argparse import Action

# Status to decide if you have to handle the error messages
CHILD_MARKER = "__E4S_CL_WORKER"

# Dry run mode, print subprocesses instead of running them
DRY_RUN = False


def is_master():
    return not os.environ.get(CHILD_MARKER, False)


def set_master():
    os.environ[CHILD_MARKER] = str(1)

class ParentStatus:
    def __enter__(self):
        set_master()

    def __exit__(self, type, value, traceback):
        os.environ.pop(CHILD_MARKER)


def is_dry_run():
    return DRY_RUN


def set_dry_run(value):
    global DRY_RUN
    DRY_RUN = value


class DryRunAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        set_dry_run(True)
