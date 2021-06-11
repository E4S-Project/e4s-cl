from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import AbstractCliView
from e4s_cl.model.profile import Profile


class DiffCommand(AbstractCliView):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt', "Compare %(model_name)ss.")
        super().__init__(*args, **kwargs)

    def _construct_parser(self):
        key_attr = self.model.key_attribute
        usage = ("%s <%s_%s> <other_%s>" %
                 (self.command, self.model_name, key_attr, key_attr))
        parser = arguments.get_model_identifier(self.model,
                                                prog=self.command,
                                                usage=usage,
                                                description=self.summary)

        parser.add_argument(self.model_name + '_rhs',
                            nargs='?',
                            type=arguments.defined_object(
                                self.model, key_attr),
                            help="The profile to compare with",
                            metavar="%s_%s" % (self.model_name, key_attr))

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        lhs = getattr(args, self.model_name)
        rhs = getattr(args, self.model_name + '_rhs')

        if not (lhs and rhs):
            raise self.parser.error("Missing profile argument")

        _order_r = lambda x, y: (list(set(x) - set(y)), '<')
        _order_l = lambda x, y: (list(set(y) - set(x)), '>')

        def _diff_member(attr, order):
            diff, sign = order(lhs[attr], rhs[attr])
            diff.sort()

            for el in diff:
                print('%s %s' % (sign, el))

        _diff_member('libraries', _order_r)
        _diff_member('files', _order_r)
        _diff_member('libraries', _order_l)
        _diff_member('files', _order_l)
        

COMMAND = DiffCommand(Profile, __name__)
