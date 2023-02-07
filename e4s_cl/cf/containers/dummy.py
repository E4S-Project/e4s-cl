"""
Dummy container used during tests
"""

from typing import List
from e4s_cl.cf.containers import Container

DEBUG_BACKEND = True
NAME = 'dummy'
EXECUTABLES = ['bash']
MIMES = []


class DummyContainer(Container):

    def run(self, command: List[str], overload: bool = True) -> int:
        pass


CLASS = DummyContainer
