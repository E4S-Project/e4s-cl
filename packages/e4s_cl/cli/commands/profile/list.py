"""
List the existing profiles in several formats
"""

from e4s_cl.cli.cli_view import ListCommand
from e4s_cl.model.profile import Profile


class ProfileListCommand(ListCommand):
    """
    Abstraction of the ListCommand to define profile specific fields to
    show in the list.
    """
    def __init__(self):
        def _count(attr):
            return lambda x: len(x.get(attr, []))

        def _selected(attr):
            return lambda x: '*' if Profile.selected().get(attr) == x[
                attr] else ' '

        dashboard_columns = [{
            'header': 'Selected',
            'function': _selected('name')
        }, {
            'header': 'Name',
            'value': 'name',
            'align': 'r'
        }, {
            'header': 'Backend',
            'value': 'backend',
            'align': 'r'
        }, {
            'header': 'Image',
            'value': 'image',
            'align': 'r'
        }, {
            'header': 'Libraries',
            'function': _count('libraries')
        }, {
            'header': 'Files',
            'function': _count('files')
        }]

        super().__init__(Profile,
                         __name__,
                         dashboard_columns=dashboard_columns)


COMMAND = ProfileListCommand()
