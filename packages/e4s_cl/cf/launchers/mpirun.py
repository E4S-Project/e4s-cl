"""mpirun launcher support"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['mpirun']

ARGUMENTS = {
    "-genv": 2,
    "-genvlist": 1,
    "-genvnone": 0,
    "-genvall": 0,
    "-f": 1,
    "-hosts": 1,
    "-wdir": 1,
    "-configfile": 1,
    "-env": 2,
    "-envlist": 1,
    "-envnone": 0,
    "-envall": 0,
    "-n": 1,
    "-np": 1
}

PARSER = Parser(ARGUMENTS)
