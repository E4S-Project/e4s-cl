"""
Profile data model.
"""

import pathlib
from e4s_cl import logger
from e4s_cl.error import InternalError, ProfileSelectionError
from e4s_cl.mvc.model import Model
from e4s_cl.mvc.controller import Controller
from e4s_cl.cf.storage.levels import USER_STORAGE

LOGGER = logger.get_logger(__name__)


def attributes():
    return {
        'name': {
            'primary_key': True,
            'type': 'string',
            'unique': True,
            'description': 'profile name',
        },
        'backend': {
            'type': 'string',
            'description': 'backend type',
        },
        'image': {
            'type': 'string',
            'description': 'image file',
        },
        'files': {
            'type': 'string',
            'description': 'files to bind',
        },
        'libraries': {
            'type': 'string',
            'description': 'libraries to bind',
        },
        'source': {
            'type': 'string',
            'description': 'script to source',
        },
    }


def homogenize_files(data):
    if not isinstance(data, dict):
        return

    files = data.get('files', [])
    data['files'] = list({pathlib.Path(f).as_posix() for f in files})


class ProfileController(Controller):
    """Profile data controller."""
    def create(self, data):
        homogenize_files(data)
        return super(ProfileController, self).create(data)

    def delete(self, keys):
        to_delete = self.one(keys)

        try:
            selected = self.selected()
        except ProfileSelectionError:
            pass
        else:
            if selected == to_delete:
                self.unselect()

        super(ProfileController, self).delete(keys)

    def select(self, profile):
        self.storage['selected_profile'] = profile.eid

    def unselect(self):
        if self.storage.contains({'key': 'selected_profile'}):
            del self.storage['selected_profile']

    def selected(self):
        try:
            selected = self.one(self.storage['selected_profile'])
            if not selected:
                raise KeyError
        except KeyError:
            raise ProfileSelectionError("No profile selected")
        else:
            return selected

    def update(self, data, keys):
        homogenize_files(data)
        super(ProfileController, self).update(data, keys)


class Profile(Model):
    """Profile data controller."""

    __attributes__ = attributes
    __controller__ = ProfileController

    @classmethod
    def controller(cls, storage=USER_STORAGE):
        return cls.__controller__(cls, storage)

    @classmethod
    def selected(cls, storage=USER_STORAGE):
        try:
            return cls.__controller__(cls, storage).selected()
        except ProfileSelectionError:
            return {}
