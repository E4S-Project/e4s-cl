from e4s_cl import EXIT_SUCCESS
from e4s_cl.error import UniqueAttributeError
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile
from e4s_cl.cf.storage.levels import PROFILE_STORAGE

class ProfileCreateCommand(CreateCommand):
    """``profile create`` subcommand."""

    def _parse_implicit(self, args, targets, applications, measurements):
        targ_ctrl = Target.controller(PROFILE_STORAGE)
        app_ctrl = Application.controller(PROFILE_STORAGE)
        meas_ctrl = Measurement.controller(PROFILE_STORAGE)
        for flag in 'impl_targets', 'impl_applications', 'impl_measurements':
            for name in getattr(args, flag, []):
                tar = targ_ctrl.one({"name": name})
                app = app_ctrl.one({"name": name})
                mes = meas_ctrl.one({"name": name})
                tam = {tar, app, mes} - {None}
                if len(tam) > 1:
                    self.parser.error("'%s' is ambiguous.  Please use --target, --application,"
                                      " or --measurement to specify configuration type" % name)
                elif not tam:
                    self.parser.error("'%s' is not a target, application, or measurement" % name)
                elif tar:
                    targets.add(tar)
                elif app:
                    applications.add(app)
                elif mes:
                    measurements.add(mes)

    def _parse_explicit(self, args, model, acc):
        ctrl = model.controller(PROFILE_STORAGE)
        model_name = model.name.lower()
        try:
            names = getattr(args, model_name)
        except AttributeError:
            pass
        else:
            for name in names:
                found = ctrl.one({"name": name})
                if not found:
                    self.parser.error('There is no %s named %s.' % (model_name, name))
                else:
                    acc.add(found)

    def _construct_parser(self):
        usage = "%s <profile_name>" % self.command
        parser = arguments.get_parser_from_model(self.model, prog=self.command, usage=usage, description=self.summary)
        parser.add_argument('impl_libraries',
                            help="Library configurations in this profile",
                            metavar='[libraries]',
                            nargs='*',
                            default=arguments.SUPPRESS)
        parser.add_argument('--libraries',
                            help="Library configurations in this profile",
                            metavar='l',
                            nargs='+',
                            default=arguments.SUPPRESS,
                            dest='libraries')
        parser.add_argument('--files',
                            help="Files configurations in this profile",
                            metavar='f',
                            nargs='+',
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

        data = {attr: getattr(args, attr) for attr in self.model.attributes if hasattr(args, attr)}
        try:
            self.model.controller().create(data)
        except UniqueAttributeError:
            self.parser.error("A profile named '%s' already exists." % args.name)

        self.logger.info("Created a new profile named '%s'.", args.name)
        return EXIT_SUCCESS

COMMAND = ProfileCreateCommand(Profile, __name__)
