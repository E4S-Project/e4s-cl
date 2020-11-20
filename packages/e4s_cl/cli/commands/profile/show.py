"""
Show a profile's configuration in detail.
"""

from e4s_cl.cli.cli_view import ShowCommand
from e4s_cl.model.profile import Profile

COMMAND = ShowCommand(Profile, __name__)
