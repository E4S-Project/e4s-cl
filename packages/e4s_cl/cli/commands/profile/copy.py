"""
Create a new profile as a copy of another existing one.
The first argument is the name of the profile to copy, the second being the destination profile.
"""

from e4s_cl.cli.cli_view import CopyCommand
from e4s_cl.model.profile import Profile

COMMAND = CopyCommand(Profile, __name__)
