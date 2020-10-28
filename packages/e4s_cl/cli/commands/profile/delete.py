"""
Delete a profile from the database
"""

from e4s_cl.cli.cli_view import DeleteCommand
from e4s_cl.model.profile import Profile

COMMAND = DeleteCommand(Profile, __name__)
