from pathlib import Path
import tests
from e4s_cl.cf.trace import opened_files


class TraceTest(tests.TestCase):
    def test_opened_files(self):
        returncode, files = opened_files(['cat', '/dev/null'])
        self.assertEqual(returncode, 0)
        self.assertIn(Path('/dev/null'), files)

    def test_return(self):
        returncode, files = opened_files(['cat', '/dev/null'])
        self.assertEqual(returncode, 0)
        for element in files:
            self.assertTrue(isinstance(element, Path))
