from e4s_cl import tests
from e4s_cl.cf.detect_name import _suffix_name


class DetectNameTests(tests.TestCase):
    def test_suffix(self):
        self.assertEqual(_suffix_name('apple', {}), 'apple')
        self.assertEqual(_suffix_name('apple', {'advanced'}), 'apple')
        self.assertEqual(_suffix_name('apple', {'applesauce'}), 'apple')
        self.assertEqual(_suffix_name('apple', {'advanced', 'apple'}),
                         'apple-2')
        self.assertEqual(_suffix_name('apple', {'advanced', 'apple-4'}),
                         'apple')
        self.assertEqual(
            _suffix_name('apple', {'advanced', 'apple', 'apple-4'}), 'apple-5')
