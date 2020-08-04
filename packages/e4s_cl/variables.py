from argparse import Action

# Status to decide if you have to handle the error messages
MASTER = True
SLAVE = False

STATUS = MASTER

# Dry run mode, print subprocesses instead of running them
DRY_RUN = False

# Debug mode, print debug info
DEBUG = False


def is_master():
    return STATUS == MASTER


def set_master(value):
    global STATUS
    STATUS = MASTER if value else SLAVE


def is_dry_run():
    return DRY_RUN


def set_dry_run(value):
    global DRY_RUN
    DRY_RUN = value


def is_debug():
    return DEBUG


def set_debug(value):
    global DEBUG
    DEBUG = value


class SlaveAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        set_master(False)


class DryRunAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        set_dry_run(True)


class DebugAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        set_debug(True)
