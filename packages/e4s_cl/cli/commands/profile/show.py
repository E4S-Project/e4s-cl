"""
Show a profile's configuration in detail.
"""

from pathlib import Path
from e4s_cl import EXIT_SUCCESS
from e4s_cl.util import color_text
from e4s_cl.cf.libraries import LibrarySet, parseELF
from e4s_cl.cli.cli_view import ShowCommand
from e4s_cl.model.profile import Profile


def bold(string):
    return color_text(string, 'white', None, ['bold'])


class ProfileShowCommand(ShowCommand):
    def _construct_parser(self):
        parser = super(ProfileShowCommand, self)._construct_parser()

        parser.add_argument("--tree",
                            action='store_true',
                            help="Output the library list as dependency trees")

        return parser

    def detail(self, profile_dict):

        outline = """%(field_name)s: %(name)s
%(field_image)s: %(image)s
%(field_backend)s: %(backend)s
%(field_script)s: %(script)s

%(field_libs)s:
%(libs)s

%(field_files)s:
%(files)s"""

        elements = {
            'field_name': bold("Profile name"),
            'field_image': bold("Container image"),
            'field_backend': bold("Container tech"),
            'field_script': bold("Pre-execution script"),
            'field_libs': bold("Bound libraries"),
            'field_files': bold("Bound files"),
        }

        elements['name'] = profile_dict.get('name', 'Not found')
        elements['image'] = profile_dict.get('image', 'Not found')
        elements['backend'] = profile_dict.get('backend', 'Not found')
        elements['script'] = profile_dict.get('source', 'None')

        if profile_dict.get('libraries'):
            elements['libs'] = "\n".join([
                " - %s (%s)" % (p.name, p.as_posix())
                for p in map(Path, profile_dict['libraries'])
            ])
        else:
            elements['libs'] = "None"

        if profile_dict.get('files'):
            elements['files'] = "\n".join(
                [" - %s" % p for p in profile_dict['files']])
        else:
            elements['files'] = "None"

        print(outline % elements)

    def tree(self, profile_dict):
        cache = LibrarySet()

        for p in map(Path, profile_dict.get('libraries', [])):
            with open(p, 'rb') as so:
                data = parseELF(so)

            cache.add(data)

        print("%s:" % bold("\nLibrary dependencies"))
        for tree in cache.trees():
            print(tree)

    def main(self, argv):
        args = self._parse_args(argv)

        self.detail(args.profile)

        if args.tree:
            self.tree(args.profile)

        return EXIT_SUCCESS


COMMAND = ProfileShowCommand(Profile, __name__)
