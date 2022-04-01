"""
This command is a helper meant to easily show differences between profiles.
It will output a list of paths prefixed by a inequality sign \
        (:code:`>`/:code:`<`) to highlight which profile has an outstanding \
        dependency.

Example
--------

.. code::

    $ e4s-cl profile diff openmpi sparse
    < /usr/lib/openmpi/libopen-pal.so.40  # Files only in the 'openmpi' profile
    < /usr/lib/openmpi/libopen-rte.so.40
    > /usr/bin/strace                     # File only in the 'sparse' module

"""

from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import AbstractCliView
from e4s_cl.model.profile import Profile


class DiffCommand(AbstractCliView):
    """
    Command outlining differences between models
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('summary_fmt', "Compare %(model_name)ss.")
        super().__init__(*args, **kwargs)

    def _construct_parser(self):
        key_attr = self.model.key_attribute
        parser = arguments.get_model_identifier(self.model,
                                                prog=self.command,
                                                description=self.summary)

        parser.add_argument(self.model_name + '_rhs',
                            type=arguments.defined_object(
                                self.model, key_attr),
                            help="The profile to compare with",
                            metavar=f"other_{self.model_name}_{key_attr}")

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        lhs = getattr(args, self.model_name)
        rhs = getattr(args, self.model_name + '_rhs')

        if isinstance(lhs, list) or isinstance(rhs, list):
            raise self.parser.error( #pylint: disable=raising-bad-type
                    f"Cannot differentiate more than 2 profiles at once, arguments don't identify 2 single profiles: "
            )

        if not (lhs and rhs):
            self.parser.error("Missing profile argument")

        _order_r = lambda x, y: (list(set(x) - set(y)), '<')
        _order_l = lambda x, y: (list(set(y) - set(x)), '>')

        def _diff_member(attr, order):
            diff, sign = order(lhs.get(attr, []), rhs.get(attr, []))
            diff.sort()

            for element in diff:
                print(f"{sign} {element}")

        _diff_member('libraries', _order_r)
        _diff_member('files', _order_r)
        _diff_member('libraries', _order_l)
        _diff_member('files', _order_l)

        return 0


COMMAND = DiffCommand(Profile, __name__)
