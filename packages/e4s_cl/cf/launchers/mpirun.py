from e4s_cl import logger

LOGGER = logger.get_logger(__name__)

ARGUMENTS = {"-genv": 2,
        "-genvlist": 1,
        "-genvnone": 0,
        "-genvall": 0,
        "-f": 1,
        "-hosts": 1,
        "-wdir": 1,
        "-configfile": 1}

LOCAL_ARGUMENTS = {"-env": 2,
        "-envlist": 1,
        "-envnone": 0,
        "-envall": 0,
        "-n": 1,
        "-np": 1}

def parse_cli(cmd):
    position = 0
    known = True
    launcher = []

    full_list = ARGUMENTS
    full_list.update(LOCAL_ARGUMENTS)

    if cmd[position] != 'mpirun':
        return [], cmd
    else:
        launcher.append(cmd[position])
        position += 1

    while known and position < len(cmd):
        LOGGER.debug("Evaluating {}".format(cmd[position]))
        if cmd[position] not in full_list.keys():
            known = False
            break

        to_skip = full_list[cmd[position]]

        for index in range(0, to_skip+1):
            launcher.append(cmd[position+index])

        position += (to_skip + 1)

    return launcher, cmd[position:]
