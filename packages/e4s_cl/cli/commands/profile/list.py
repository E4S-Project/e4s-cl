from e4s_cl import util
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import ListCommand
from e4s_cl.model.profile import Profile

class ProfileListCommand(ListCommand):
    def __init__(self):
        def _name_list(attr):
            return lambda x: ', '.join([p for p in x.get(attr, [])])

        def _count(attr):
            return lambda x: len(x.get(attr, []))

        def _selected(attr):
            return lambda x: '*' if Profile.selected().get(attr) == x[attr] else ' '

        dashboard_columns = [
                {'header': 'Selected', 'function': _selected('name')},
                {'header': 'Name', 'value': 'name', 'align': 'r'},
                {'header': 'Backend', 'value': 'backend', 'align': 'r'},
                {'header': 'Image', 'value': 'image', 'align': 'r'},
                {'header': 'Libraries', 'function': _count('libraries')},
                {'header': 'Files', 'function': _count('files')}
                ]

        super(ProfileListCommand, self).__init__(Profile, __name__, dashboard_columns=dashboard_columns)

    def main(self, argv):
        """Command program entry point.

        Args:
            argv (list): Command line arguments.

        Returns:
            int: Process return code: non-zero if a problem occurred, 0 otherwise
        """
        args = self._parse_args(argv)
        style_args = ['--' + args.style] if hasattr(args, 'style') else []
        levels = arguments.parse_storage_flag(args)
        keys = getattr(args, 'keys', [])
        single = (len(keys) == 1 and len(levels) == 1)

        if single:
            prof_name = keys[0]
            self.title_fmt = "{} Configuration (%(storage_path)s)".format(prof_name)
            # Remove the selected field if listing a single profile
            self.dashboard_columns = self.dashboard_columns[1:]

        retval = super(ProfileListCommand, self).main(argv)

        if single:
            storage = levels[0]
            ctrl = Profile.controller(storage)
            prof = ctrl.one({'name': keys[0]})
            for attr in ['libraries', 'files']:
                print("{} bound in profile:".format(attr.capitalize()))
                print("\n{}\n".format("\n".join(prof.get(attr, []))))

        return retval

COMMAND = ProfileListCommand()
