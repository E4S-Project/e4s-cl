import tests
from copy import deepcopy
from pathlib import Path
from e4s_cl.error import ProfileSelectionError
from e4s_cl.model.profile import Profile, homogenize_files

P_NAME = dict(name='profile')

BASE_DATA = dict(name='test',
                 files=['/dev/a', '/dev/b', '/dev/c'],
                 libraries=[])

PATCHES = [
    dict(name='new_name'),
    dict(files=['/etc/apptainer']),
    dict(libraries=['/not/a/lib.so'])
]


class ModelProfileTest(tests.TestCase):

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()
        self.assertFalse(Profile.controller().all())

    def test_create(self):
        controller = Profile.controller()
        profile = controller.create(BASE_DATA)

        created = controller.one(profile.eid)

        self.assertDictEqual(profile, BASE_DATA)
        self.assertDictEqual(created, BASE_DATA)

    def test_create_same_name(self):
        controller = Profile.controller()
        profile = controller.create(P_NAME)

        with self.assertRaises(Exception):
            controller.create(P_NAME)

    def test_create_no_name(self):
        controller = Profile.controller()

        with self.assertRaises(Exception):
            controller.create(dict(files=[]))

    def test_update_same_name(self):
        controller = Profile.controller()
        controller.create(P_NAME)
        profile = controller.create(dict(name='another_profile'))

        with self.assertRaises(Exception):
            controller.update(P_NAME, dict(name='another_profile'))

    def test_update_no_match(self):
        controller = Profile.controller()
        with self.assertRaises(Exception):
            controller.update(P_NAME, dict(name='another_profile'))

    def test_delete(self):
        controller = Profile.controller()

        controller.create(P_NAME)
        self.assertTrue(controller.all())
        controller.delete(P_NAME)
        self.assertFalse(controller.all())

        profile = controller.create(P_NAME)
        self.assertTrue(controller.all())
        controller.delete(profile)
        self.assertFalse(controller.all())

    def test_select_eid(self):
        controller = Profile.controller()

        profile = controller.create(P_NAME)
        controller.select(profile)
        self.assertEqual(controller.selected(), profile)

    def test_select_data(self):
        controller = Profile.controller()

        profile = controller.create(P_NAME)
        controller.select(P_NAME)
        self.assertEqual(controller.selected(), profile)

    def test_select_empty(self):
        controller = Profile.controller()

        with self.assertRaises(ProfileSelectionError):
            controller.selected()

    def test_select_no_match(self):
        controller = Profile.controller()
        with self.assertRaises(ProfileSelectionError):
            controller.select(P_NAME)

    def testHomogenization(self):
        paths = ['/proc/', '///mnt/../test///']
        posix = list(map(lambda x: Path(x).as_posix(), paths))
        data = dict(files=paths)
        homogenize_files(data)

        self.assertListEqual(posix, data['files'])

        data = dict()
        self.assertNotIn('files', data)


def wrapper_update(patch):

    def generated(self):
        controller = Profile.controller()
        profile = controller.create(BASE_DATA)

        expected = deepcopy(BASE_DATA)
        expected.update(patch)
        controller.update(patch, profile.eid)
        updated = controller.one(profile.eid)

        self.assertDictEqual(updated, expected)

    generated.__name__ = f"test_update_{' '.join(patch)}"
    return generated


for patch in PATCHES:
    test_update = wrapper_update(patch)
    setattr(ModelProfileTest, test_update.__name__, test_update)
