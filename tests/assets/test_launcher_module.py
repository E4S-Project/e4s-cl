"""
Test launcher module
"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['mylauncher']

ARGUMENTS = {
    "-a": 0,
    "-b": 1,
    "-c": 5,
}

META = dict(reserved_directories=['/reserved'])

PARSER = Parser(ARGUMENTS)
