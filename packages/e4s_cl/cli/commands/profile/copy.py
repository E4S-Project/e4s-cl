"""
Copy a profile to another new profile
"""

from e4s_cl.cli.cli_view import CopyCommand
from e4s_cl.model.profile import Profile

COMMAND = CopyCommand(Profile, __name__)
