"""
Module grouping all the profile configuration commands.
Accessible via `e4s-cl profile <command>`.
"""

from e4s_cl.cli.cli_view import RootCommand
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.detect import COMMAND as detect_command


def _profile_fields():
    for name, data in Profile.__attributes__().items():
        yield " - %(name)s: %(description)s" % {
            'name': name.capitalize(),
            'description': data['description'].capitalize()
        }


HELP_PAGE = """The profile command is used to access and manage profiles.

e4s-cl uses profiles to keep track of execution parameters. These parameters
can then be omitted from the command line given the corresponding profile.

Profiles have the following fields:
%(detail)s

It is highly encouraged to use e4s-cl facilities to create profiles.
The %(detect)s command will complete the selected profile
from the execution of the command passed as an argument. This is the most
secure way to get a accurate profile.

The e4s-cl init command will create a new profile from the available
MPI library, using generic arguments. Those arguments may not correspond to
real use-cases and may result in an incomplete profile.""" % {
    'detect': detect_command.command,
    'detail': "\n".join(_profile_fields())
}

COMMAND = RootCommand(Profile,
                      __name__,
                      group="configuration",
                      help_page_fmt=HELP_PAGE)
