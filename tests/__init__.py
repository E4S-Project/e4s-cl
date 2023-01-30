"""Unit test initializations and utility functions."""

import os
import sys
import glob
import shutil
import shlex
import atexit
import tempfile
import unittest
from unittest import skipIf, skipUnless
from pathlib import Path
from e4s_cl.util import get_command_output
import warnings
from io import StringIO
from e4s_cl import logger, E4S_CL_HOME, EXIT_SUCCESS, EXIT_FAILURE, config

ASSETS = Path(__file__).parent / "assets"
CONFIGURATION_FILE = ASSETS / "e4s-cl.yaml"

# Set the configuration to a specific testing version
config.update_configuration(
    config.Configuration.create_from_file(CONFIGURATION_FILE))

from e4s_cl.error import ConfigurationError
from e4s_cl.cf.storage.levels import USER_STORAGE, SYSTEM_STORAGE
from e4s_cl.cf.assets import SAMPLE_BINARY_TABLE, BUILTIN_PROFILE_TABLE

_NOT_IMPLEMENTED = []


def not_implemented(cls):
    """Decorator for TestCase classes to indicate that the tests have not been written (yet)."""
    msg = "%s: tests have not been implemented" % cls.__name__
    _NOT_IMPLEMENTED.append(msg)
    return unittest.skip(msg)(cls)


def _null_decorator(_):
    return _


class TestCase(unittest.TestCase):
    """Base class for unit tests.

    Performs tests in a temporary directory and reconfigures :any:`e4s_cl.logger` to work with :any:`unittest`.
    """
    # Follow the :any:`unittest` code style.
    # pylint: disable=invalid-name

    @classmethod
    def setUpClass(cls):
        # Reset stdout logger handler to use buffered unittest stdout
        # pylint: disable=protected-access
        cls._orig_stream = logger._STDERR_HANDLER.stream
        logger._STDERR_HANDLER.stream = sys.stdout

        # Make sure the storage is clean before any test is performed
        cls.resetStorage()

    @classmethod
    def tearDownClass(cls):
        # Reset stdout logger handler to use original stdout
        # pylint: disable=protected-access
        logger._STDERR_HANDLER.stream = cls._orig_stream

    def run(self, result=None):
        # Whenever running a test, set the terminal size large enough to avoid any regex failures due to line wrap
        logger.TERM_SIZE = (150, 150)
        logger.LINE_WIDTH = logger.TERM_SIZE[0]
        logger._STDERR_HANDLER.setFormatter(
            logger.LogFormatter(line_width=logger.LINE_WIDTH,
                                printable_only=True))
        # Nasty hack to give us access to what sys.stderr becomes when unittest.TestRunner.buffered == True
        # pylint: disable=attribute-defined-outside-init
        assert result is not None
        self._result_stream = result.stream
        return super(TestCase, self).run(result)

    def exec_command(self, cmd, argv):
        """Execute a e4s_cl command's main() routine and return the exit code, stdout, and stderr data.

        Args:
            cmd (type): A command instance that has a `main` callable attribute.
            argv (list): Arguments to pass to cmd.main()

        Returns:
            tuple: (retval, stdout, stderr) results of running the command.
        """

        if isinstance(argv, str):
            argv = shlex.split(argv)

        # pylint: disable=protected-access
        stdout = tempfile.TemporaryFile(mode='w+', buffering=1)
        stderr = tempfile.TemporaryFile(mode='w+', buffering=1)
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout, stderr
            logger._STDERR_HANDLER.stream = stderr
            try:
                retval = cmd.main(argv)
            except SystemExit as err:
                retval = err.code
            stdout.seek(0), stderr.seek(0)
            stdout_value, stderr_value = stdout.read(), stderr.read()
            return retval, stdout_value, stderr_value
        finally:
            sys.stdout, sys.stderr = orig_stdout, orig_stderr
            stdout.close(), stderr.close()
            logger._STDERR_HANDLER.stream = orig_stdout

    def assertCommandReturnValue(self, return_value, cmd, argv):
        retval, stdout, stderr = self.exec_command(cmd, argv)
        if retval != return_value:
            print(stderr, file=sys.stderr)
        self.assertEqual(retval, return_value)
        return stdout, stderr

    def assertNotCommandReturnValue(self, return_value, cmd, argv):
        retval, stdout, stderr = self.exec_command(cmd, argv)
        if retval == return_value:
            print(stderr, file=sys.stderr)
        self.assertNotEqual(retval, return_value)
        return stdout, stderr

    def assertContainsInOrder(self, subset, ordered_iterable):
        """Asserts the ordered_iterable contains the elements of the subset,
        in order, with possibly elements in between"""
        matches = list(filter(lambda x: x in subset, ordered_iterable))

        self.assertListEqual(subset, matches)

    @classmethod
    def resetStorage(cls):
        tables = ["Profile", SAMPLE_BINARY_TABLE, BUILTIN_PROFILE_TABLE]
        for table in tables:
            USER_STORAGE.purge(table_name=table)
            SYSTEM_STORAGE.purge(table_name=table)


class TestRunner(unittest.TextTestRunner):
    """Test suite runner."""

    def __init__(self, *args, **kwargs):
        super(TestRunner, self).__init__(*args, **kwargs)
        self.buffer = True

    def run(self, test):
        result = super(TestRunner, self).run(test)
        for item in _NOT_IMPLEMENTED:
            print("WARNING: %s" % item)
        if result.wasSuccessful():
            return EXIT_SUCCESS
        return EXIT_FAILURE
