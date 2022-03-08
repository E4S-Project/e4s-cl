import re
import tests
from e4s_cl.cli.arguments import get_parser

parser_usage = 'do not use'
parser_description = 'This parser is a test'
parser_epilog = 'Bye bye'

optional_title = '--option'
optional_help = 'This is help'
optional_metavar = 'value'


class ArgumentsTests(tests.TestCase):
    def setUp(self):
        parser = get_parser(__name__,
                            usage=parser_usage,
                            description=parser_description,
                            epilog=parser_epilog)

        parser.add_argument(optional_title,
                            help=optional_help,
                            metavar=optional_metavar)

        self.help_string = parser.format_help()

    def test_optional(self):
        pattern = re.compile(
            f"{optional_title}.*{optional_metavar}.*{optional_help}")

        self.assertTrue(re.search(pattern, self.help_string))

    def test_usage(self):
        self.assertTrue(re.search(parser_usage, self.help_string))

    def test_description(self):
        self.assertTrue(re.search(parser_description, self.help_string))

    def test_epilog(self):
        self.assertTrue(re.search(parser_epilog, self.help_string))
