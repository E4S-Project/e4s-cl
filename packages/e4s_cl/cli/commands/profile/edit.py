from pathlib import Path
from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.logger import get_logger
from e4s_cl.cli.cli_view import EditCommand
from e4s_cl.model.profile import Profile

LOGGER = get_logger(__name__)


class ProfileEditCommand(EditCommand):
    """``profile edit`` subcommand."""
    def _construct_parser(self):
        usage = "%s <profile_name> [arguments]" % self.command
        parser = arguments.get_parser_from_model(self.model,
                                                 use_defaults=False,
                                                 prog=self.command,
                                                 usage=usage,
                                                 description=self.summary)
        parser.add_argument('--new_name',
                            help="change the profile's name",
                            metavar='<new_name>',
                            dest='new_name',
                            default=arguments.SUPPRESS)
        parser.add_argument('--backend',
                            help="change the profile's container technology",
                            metavar='<backend>',
                            dest='backend',
                            default=arguments.SUPPRESS)
        parser.add_argument('--image',
                            help="change the profile's image",
                            metavar='<image>',
                            dest='image',
                            default=arguments.SUPPRESS)
        parser.add_argument('--add-files',
                            help="Add files to the profile",
                            metavar='<file>',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS)
        parser.add_argument('--remove-files',
                            help="Remove files from the profile",
                            metavar='<file>',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS)
        parser.add_argument('--add-libraries',
                            help="Add libraries to the profile",
                            metavar='<library>',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS)
        parser.add_argument('--remove-libraries',
                            help="Remove libraries from the profile",
                            metavar='<library>',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS)
        return parser

    def _parse_add_args(self, args, prof):
        added = set()
        for arg, attr in [('add_files', 'files'),
                          ('add_libraries', 'libraries')]:
            names = getattr(args, arg, [])
            for file_name in [Path(n).as_posix() for n in names]:
                if file_name and file_name not in prof.get(attr, []):
                    added.add(file_name)
                    prof[attr] = prof.get(attr, []) + [file_name]
                else:
                    LOGGER.error("File %s already in profile's %s", file_name,
                                 attr)

        return added

    def _parse_remove_args(self, args, prof):
        removed = set()
        for arg, attr in [('remove_files', 'files'),
                          ('remove_libraries', 'libraries')]:
            names = getattr(args, arg, [])
            for file_name in [Path(n).as_posix() for n in names]:
                if file_name and file_name in prof.get(attr, []):
                    removed.add(file_name)
                    prof[attr].remove(file_name)
                else:
                    LOGGER.error("File %s not in profile's %s", file_name,
                                 attr)

        return removed

    def main(self, argv):
        from e4s_cl.cli.commands.profile.list import COMMAND as profile_list
        args = self._parse_args(argv)

        prof_ctrl = Profile.controller()

        profile_name = args.name
        profile = prof_ctrl.one({'name': profile_name})
        if not profile:
            self.parser.error(
                "'%s' is not a profile name. Type `%s` to see valid names." %
                (profile_name, profile_list.command))

        updates = dict(profile)
        updates['name'] = getattr(args, 'new_name', profile.get('name'))
        updates['backend'] = getattr(args, 'backend', profile.get('backend'))
        updates['image'] = getattr(args, 'image', profile.get('image'))

        added = self._parse_add_args(args, updates)
        removed = self._parse_remove_args(args, updates)

        prof_ctrl.update(updates, {'name': profile_name})
        for data in added:
            self.logger.info("Added %s to profile configuration '%s'.", data,
                             profile_name)
        for data in removed:
            self.logger.info("Removed %s from profile configuration '%s'.",
                             data, profile_name)
        return EXIT_SUCCESS


COMMAND = ProfileEditCommand(Profile, __name__)
