"""
Dummy container used during tests
"""

from e4s_cl.cf.containers import Container

DEBUG_BACKEND = True
NAME = 'dummy'
EXECUTABLES = ['bash']
MIMES = []


class DummyContainer(Container):
    def run(self, command, redirect_stdout=False):
        pass


CLASS = DummyContainer
