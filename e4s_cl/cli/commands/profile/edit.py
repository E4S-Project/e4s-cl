"""
Modify the profile associated to the name passed as an argument.

Passing a value to the options **--name**, **--backend**, \
**--image**, **--source** will overwrite the profile's corresponding field.

Passing a value to **--add-files**, **--remove-files**, **--add-libraries**, \
**--remove-libraries** will add or remove elements from the list \
of files or libraries, accordingly.

The name argument can be omitted, in which case the selected profile is modified.
"""

from pathlib import Path
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE
from e4s_cl.error import UniqueAttributeError
from e4s_cl.cli import arguments
from e4s_cl.logger import get_logger
from e4s_cl.cli.cli_view import EditCommand
from e4s_cl.model.profile import Profile
from e4s_cl.cf.containers import EXPOSED_BACKENDS

LOGGER = get_logger(__name__)


class ProfileEditCommand(EditCommand):
    """``profile edit`` subcommand."""

    def _construct_parser(self):
        usage = f"{self.command} <profile_name> [arguments]"
        parser = arguments.get_model_identifier(self.model,
                                                prog=self.command,
                                                usage=usage,
                                                description=self.summary)

        parser.add_argument('--name',
                            help="change the profile's name",
                            metavar='<name>',
                            dest='name',
                            default=arguments.SUPPRESS)

        parser.add_argument(
            '--backend',
            help="change the profile's container technology." +
            f" Available backends are: {', '.join(EXPOSED_BACKENDS)}",
            metavar='<backend>',
            dest='backend',
            default=arguments.SUPPRESS)

        parser.add_argument('--image',
                            help="change the profile's image",
                            metavar='<path/to/image>',
                            dest='image',
                            type=str,
                            default=arguments.SUPPRESS)

        parser.add_argument('--source',
                            help="change the profile's setup script",
                            metavar='<path/to/script>',
                            dest='source',
                            type=arguments.posix_path,
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

        parser.add_argument('--wi4mpi',
                            help="Root of the WI4MPI installation to use",
                            metavar='<path>',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS)

        parser.add_argument('--wi4mpi_options',
                            help="Options to use with WI4MPI",
                            metavar='<args>',
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
        args = self._parse_args(argv)
        controller = Profile.controller()

        profile = args.profile
        profile_name = profile.get('name')

        updates = dict(profile)

        fields = {
            'name', 'backend', 'image', 'source', 'wi4mpi', 'wi4mpi_options'
        }

        for field in fields:
            updates[field] = getattr(args, field, profile.get(field))

        for data in self._parse_add_args(args, updates):
            self.logger.info("Added %s to profile configuration '%s'.", data,
                             profile_name)

        for data in self._parse_remove_args(args, updates):
            self.logger.info("Removed %s from profile configuration '%s'.",
                             data, profile_name)

        try:
            controller.update(updates, {'name': profile_name})
        except UniqueAttributeError:
            LOGGER.error("Invalid parameters for edition: %s=%s",
                         Profile.key_attribute, updates[Profile.key_attribute])
            return EXIT_FAILURE

        return EXIT_SUCCESS


COMMAND = ProfileEditCommand(Profile, __name__)
