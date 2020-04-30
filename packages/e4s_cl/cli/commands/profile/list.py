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

        dashboard_columns = [
                {'header': 'Name', 'value': 'name', 'align': 'r'},
                {'header': 'Backend', 'value': 'backend', 'align': 'r'},
                {'header': 'Image', 'value': 'image', 'align': 'r'},
                {'header': 'Libraries', 'function': _name_list('libraries')},
                {'header': 'Files', 'function': _name_list('files')}
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

        retval = super(ProfileListCommand, self).main(argv)

        """if single:
            proj_name = keys[0]
            self.title_fmt = "Profile Configuration (%(storage_path)s)"
            experiment_list_cmd.title_fmt = "Experiments in profile '%s'" % proj_name

        if single:
            storage = levels[0]
            ctrl = Profile.controller(storage)
            proj = ctrl.one({'name': keys[0]})
            for cmd, prop in ((target_list_cmd, 'targets'),
                              (application_list_cmd, 'applications'),
                              (measurement_list_cmd, 'measurements'),
                              (experiment_list_cmd, 'experiments')):
                primary_key = proj.attributes[prop]['collection'].key_attribute
                records = proj.populate(prop)
                if records:
                    cmd.main([record[primary_key] for record in records] + style_args)
                else:
                    label = util.color_text('%s: No %s' % (proj['name'], prop), color='red', attrs=['bold'])
                    print("%s.  Use `%s` to view available %s.\n" % (label, cmd, prop))
        """
        return retval

COMMAND = ProfileListCommand()
