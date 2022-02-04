"""
Detail a profile's content and fields.
The name argument can be omitted in case a profile is selected, in which case the selected profile is shown.
"""

from pathlib import Path
from e4s_cl import EXIT_SUCCESS
from e4s_cl.util import color_text
from e4s_cl.cf.libraries import LibrarySet, Library
from e4s_cl.cli.cli_view import ShowCommand
from e4s_cl.model.profile import Profile


def bold(string):
    return color_text(string, 'white', None, ['bold'])


class ProfileShowCommand(ShowCommand):
    """
    Output details about a profile
    """
    def _construct_parser(self):
        parser = super()._construct_parser()

        return parser

    def detail(self, profile_dict):
        """
        Format template for the output
        """

        outline = """%(field_name)s: %(name)s
%(field_image)s: %(image)s
%(field_backend)s: %(backend)s
%(field_script)s: %(script)s
%(field_wi4mpi)s: %(wi4mpi)s
%(field_wi4mpi_options)s: %(wi4mpi_options)s

%(field_libs)s:
%(libs)s

%(field_files)s:
%(files)s"""

        headers = {
            'field_name': bold("Profile name"),
            'field_image': bold("Container image"),
            'field_backend': bold("Container tech"),
            'field_script': bold("Pre-execution script"),
            'field_libs': bold("Bound libraries"),
            'field_files': bold("Bound files"),
            'field_wi4mpi': bold("WI4MPI"),
            'field_wi4mpi_options': bold("WI4MPI options"),
        }

        elements = {
            'name': profile_dict.get('name', 'Not found'),
            'image': profile_dict.get('image', 'Not found'),
            'backend': profile_dict.get('backend', 'Not found'),
            'script': profile_dict.get('source', 'None'),
            'wi4mpi': profile_dict.get('wi4mpi', 'None'),
            'wi4mpi_options': profile_dict.get('wi4mpi_options', 'None'),
        }

        if profile_dict.get('libraries'):
            elements['libs'] = "\n".join([
                f" - {p.name} ({p.as_posix()})"
                for p in map(Path, profile_dict['libraries'])
            ])
        else:
            elements['libs'] = "None"

        if profile_dict.get('files'):
            elements['files'] = "\n".join(
                [f" - {p}" for p in profile_dict['files']])
        else:
            elements['files'] = "None"

        print(outline % {**headers, **elements})

    def main(self, argv):
        args = self._parse_args(argv)

        self.detail(args.profile)

        return EXIT_SUCCESS


COMMAND = ProfileShowCommand(Profile, __name__)
