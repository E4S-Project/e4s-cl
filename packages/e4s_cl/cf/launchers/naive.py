"""naive launcher support - for testing"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['naive']

ARGUMENTS = {"-n": 1}

PARSER = Parser(ARGUMENTS)
