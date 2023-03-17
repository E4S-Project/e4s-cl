
"""
Tests ensuring the init command behaves as intented relating to wi4mpi
"""

import os
import sys
from itertools import combinations
import tests
from e4s_cl.util import which
from e4s_cl.model.profile import Profile
from e4s_cl.cf.libraries import resolve
from e4s_cl.cf.assets import add_builtin_profile, remove_builtin_profile
from e4s_cl.cli.commands.init import COMMAND, _compile_sample
from e4s_cl import logger
import unittest

TEST_SYSTEM = '__test_system'

MPICC = os.environ.get('__E4SCL_MPI_COMPILER', 'mpicc')


class InitTestWI4MPI(tests.TestCase):
    """
    Partial class definition: more tests are defined below
    """
    
    @classmethod
    def setUpClass(cls):
        # Reset stdout logger handler to use buffered unittest stdout
        # pylint: disable=protected-access
        cls._orig_stream = logger._STDERR_HANDLER.stream
        logger._STDERR_HANDLER.stream = sys.stdout

        # Make sure the storage is clean before any test is performed
        cls.resetStorage()
        try:
            if (_compile_sample(which(MPICC)) == None):
                raise unittest.SkipTest('MPI compiler failed to compile sample: related tests will be skipped')
        except FileNotFoundError:
            raise unittest.SkipTest('No MPI compiler found: related tests will be skipped')
        
    def setUp(self):
        add_builtin_profile(TEST_SYSTEM, {'name': TEST_SYSTEM})

    def tearDown(self):
        remove_builtin_profile(TEST_SYSTEM)
        Profile.controller().unselect()
        self.resetStorage()

    @tests.skipUnless(which(MPICC), "No MPI compiler found")
    def test_wi4mpi(self):
        self.assertCommandReturnValue(0, COMMAND,
                                      "--wi4mpi /path/to/installation")
        profile = Profile.controller().selected()

        self.assertTrue(profile)
        self.assertEqual(profile.get('wi4mpi'), '/path/to/installation')

    @tests.skipUnless(which(MPICC), "No MPI compiler found")
    def test_wi4mpi_overwrite(self):
        self.assertCommandReturnValue(0, COMMAND,
                                      "--wi4mpi /path/to/installation")
        self.assertEqual(Profile.controller().count(), 1)
        self.assertCommandReturnValue(0, COMMAND,
                                      "--wi4mpi /path/to/installation")
        self.assertEqual(Profile.controller().count(), 1)
    
    @tests.skipUnless(which(MPICC), "No MPI compiler found")
    def test_rename_wi4mpi(self):
        self.assertCommandReturnValue(
            0, COMMAND,
            "--profile init_test_profile --wi4mpi /path/to/installation")
        profile = Profile.controller().selected()

        self.assertTrue(profile)
        self.assertEqual(profile.get('name'), 'init_test_profile')
        self.assertEqual(profile.get('wi4mpi'), '/path/to/installation')
