"""
Profile data model.
"""

from pathlib import Path
from e4s_cl import logger
from e4s_cl.error import ProfileSelectionError
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
        "wi4mpi": {
            'type': 'string',
            'description': 'root of the wi4mpi installation to use (optional)',
        },
        'backend': {
            'type': 'string',
            'description': 'container backend technology',
        },
        'image': {
            'type': 'string',
            'description': 'image identifier',
        },
        'files': {
            'type': 'list',
            'description': 'files to bind in the container',
        },
        'libraries': {
            'type': 'list',
            'description': 'libraries to bind in the container',
        },
        'source': {
            'type': 'string',
            'description': 'script to source before execution (optional)',
        },
    }


def homogenize_files(data: dict) -> None:
    """Cast all paths to posix-compliant format"""
    if not isinstance(data, dict) or 'files' not in data:
        return

    def _sanitize(path: str) -> str:
        return Path(path).as_posix()

    data['files'] = list(map(_sanitize, data.get('files', [])))


class ProfileController(Controller):
    """Profile data controller."""

    def create(self, data):
        homogenize_files(data)
        return super().create(data)

    def delete(self, keys):
        to_delete = self.one(keys)

        try:
            selected = self.selected()
        except ProfileSelectionError:
            pass
        else:
            if selected == to_delete:
                self.unselect()

        super().delete(keys)

    def select(self, keys):
        """Mark a profile as selected"""
        to_select = self.one(keys)

        if to_select is not None:
            self.storage['selected_profile'] = to_select.eid
        else:
            raise ProfileSelectionError('No matching profile')

    def unselect(self):
        if self.storage.contains({'key': 'selected_profile'}):
            del self.storage['selected_profile']

    def selected(self):
        try:
            selected = self.one(self.storage['selected_profile'])
            if not selected:
                raise KeyError
        except KeyError as key_err:
            raise ProfileSelectionError("No profile selected") from key_err
        else:
            return selected

    def update(self, data, keys):
        homogenize_files(data)
        super().update(data, keys)


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
