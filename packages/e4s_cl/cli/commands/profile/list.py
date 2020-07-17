import texttable
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import ListCommand
from e4s_cl.model.profile import Profile


class ProfileListCommand(ListCommand):
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

        super(ProfileListCommand,
              self).__init__(Profile,
                             __name__,
                             dashboard_columns=dashboard_columns)

    def main(self, argv):
        """Command program entry point.

        Args:
            argv (list): Command line arguments.

        Returns:
            int: Process return code: non-zero if a problem occurred, 0 otherwise
        """
        args = self._parse_args(argv)

        retval = super(ProfileListCommand, self).main(argv)

        return retval


COMMAND = ProfileListCommand()
