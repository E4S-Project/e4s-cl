import tests
from copy import deepcopy
from pathlib import Path
from e4s_cl.model.profile import Profile, homogenize_files


class ProfileModelTest(tests.TestCase):

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def testHomogenization(self):
        paths = ['/proc/', '///mnt/../test///']
        posix = list(map(lambda x: Path(x).as_posix(), paths))
        data = dict(files=paths)
        homogenize_files(data)

        self.assertListEqual(posix, data['files'])

        data = dict()
        self.assertNotIn('files', data)


BASE_DATA = dict(name='test',
                 files=['/dev/a', '/dev/b', '/dev/c'],
                 libraries=[])

PATCHES = [
    dict(name='new_name'),
    dict(files=['/etc/apptainer']),
    dict(libraries=['/not/a/lib.so'])
]


def wrapper(patch):

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
    test = wrapper(patch)
    setattr(ProfileModelTest, test.__name__, test)
