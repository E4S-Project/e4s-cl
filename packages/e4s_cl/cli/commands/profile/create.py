from e4s_cl import EXIT_SUCCESS
from e4s_cl.error import UniqueAttributeError
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile


class ProfileCreateCommand(CreateCommand):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = "%s <profile_name>" % self.command
        parser = arguments.get_parser_from_model(self.model,
                                                 prog=self.command,
                                                 usage=usage,
                                                 description=self.summary)
        parser.add_argument('impl_libraries',
                            help="Library configurations in this profile",
                            metavar='[libraries]',
                            nargs='*',
                            default=arguments.SUPPRESS)
        parser.add_argument('--libraries',
                            help="Library configurations in this profile",
                            metavar='l',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS,
                            dest='libraries')
        parser.add_argument('--files',
                            help="Files configurations in this profile",
                            metavar='f',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS,
                            dest='files')
        parser.add_argument('--backend',
                            help="Container backend for this profile",
                            metavar='b',
                            default=arguments.SUPPRESS,
                            dest='backend')
        parser.add_argument('--image',
                            help="Container image for this profile",
                            metavar='i',
                            default=arguments.SUPPRESS,
                            dest='image')
        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        data = {
            attr: getattr(args, attr)
            for attr in self.model.attributes if hasattr(args, attr)
        }
        try:
            self.model.controller().create(data)
        except UniqueAttributeError:
            self.parser.error("A profile named '%s' already exists." %
                              args.name)

        self.logger.info("Created a new profile named '%s'.", args.name)
        return EXIT_SUCCESS


COMMAND = ProfileCreateCommand(Profile, __name__)
