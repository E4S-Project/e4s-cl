"""
Tests ensuring the init command behaves as intented
"""

import os
from itertools import combinations
import tests
from tests import TEST_SYSTEM
from e4s_cl.util import which
from e4s_cl.model.profile import Profile
from e4s_cl.cf.libraries import resolve
from e4s_cl.cli.commands.init import COMMAND


class InitTest(tests.TestCase):
    """
    Partial class definition: more tests are defined below
    """

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()


options = [
    ('--mpi', '/path/to/installation'),
    ('--launcher', '/path/to/binary'),
    ('--launcher_args', "'-np 8192'"),
    ('--wi4mpi', "/tmp"),
]
