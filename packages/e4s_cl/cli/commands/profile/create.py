"""
Create a profile from CLI arguments
"""

from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile
from e4s_cl.cf.containers import EXPOSED_BACKENDS


class ProfileCreateCommand(CreateCommand):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = "%s <profile_name>" % self.command
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
            " Available backends are: %s" % ", ".join(EXPOSED_BACKENDS),
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

        return parser

SUMMARY = "Create a profile. %(prog)s uses profiles to record information about MPI libraries and simplify the launch commands."

COMMAND = ProfileCreateCommand(Profile, __name__, summary_fmt=SUMMARY)
