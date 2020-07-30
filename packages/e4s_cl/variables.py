MASTER = True
SLAVE = False

STATUS = MASTER

DRY_RUN = False


def is_master():
    return STATUS == MASTER


def is_dry_run():
    return DRY_RUN


def set_dry_run(value):
    global DRY_RUN
    DRY_RUN = value
