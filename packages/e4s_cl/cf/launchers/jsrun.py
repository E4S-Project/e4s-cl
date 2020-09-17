"""jsrun launcher support"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['jsrun']

ARGUMENTS = {
    "-a": 1,
    "-p": 1,
    "-c": 1,
    "-d": 1,
    "-g": 1,
    "-K": 1,
    "-l": 1,
    "-m": 1,
    "-n": 1,
    "-r": 1,
    "-e": 1,
    "-f": 1,
    "-I": 1,
    "-k": 1,
    "-o": 1,
    "-t": 1,
    "-h": 1,
    "-A": 1,
    "-H": 1,
    "-i": 0,
    "--immediate": 0,
    "-J": 1,
    "-L": 1,
    "-M": 1,
    "-P": 1,
    "-S": 1,
    "-U": 1,
    "-x": 1,
    "-X": 1,
    "-Z": 1,
    "-b": 1,
    "-D": 1,
    "-E": 1,
    "-F": 1,
    "-?": 0,
    "--help": 0,
    "--usage": 0,
    "-V": 0,
    "--version": 0,
}

PARSER = Parser(ARGUMENTS)
