"""
This command creates a new profile with the name passed as the first argument.
Options control the data added to the fields of the newly-created profile.

.. warning::

    MPI libraries often dynamically use files and libraries without warning, \
            and the absence of those unlisted files during execution more \
            often than not results in a crash or segmentation fault. Please \
            ensure you acknowledge the result of \
            :ref:`profile detect<profile_detect>` when creating an empty profile.

"""

from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile
from e4s_cl.cf.containers import EXPOSED_BACKENDS


class ProfileCreateCommand(CreateCommand):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = f"{self.command} <profile_name>"
        parser = arguments.get_parser_from_model(self.model,
                                                 prog=self.command,
                                                 usage=usage,
                                                 description=self.summary)
        parser.add_argument(
            '--libraries',
            help="Comma-separated list of libraries to add to this profile",
            metavar='l1.so,l2.so,...',
            type=arguments.posix_path_list,
            default=arguments.SUPPRESS,
            dest='libraries')

        parser.add_argument(
            '--files',
            help="Comma-separated list of files to add to this profile",
            metavar='f1,f2,...',
            type=arguments.posix_path_list,
            default=arguments.SUPPRESS,
            dest='files')

        parser.add_argument(
            '--backend',
            help="Container backend for this profile" +
            f" Available backends are: {', '.join(EXPOSED_BACKENDS)}",
            metavar='technology',
            default=arguments.SUPPRESS,
            dest='backend')

        parser.add_argument('--image',
                            help="Path to a image for this profile",
                            metavar='path/to/image',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS,
                            dest='image')

        parser.add_argument(
            '--source',
            help="Path to a bash script to source before execution",
            metavar='path/to/script',
            type=arguments.posix_path,
            default=arguments.SUPPRESS,
            dest='source')

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


SUMMARY = "Create a profile."

COMMAND = ProfileCreateCommand(Profile, __name__, summary_fmt=SUMMARY)
