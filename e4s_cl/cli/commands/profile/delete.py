"""
Delete the profile associated with the name passed as an argument.
"""

from e4s_cl.cli.cli_view import DeleteCommand
from e4s_cl.model.profile import Profile

COMMAND = DeleteCommand(Profile, __name__)
