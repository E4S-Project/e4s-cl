"""
Module grouping all the profile configuration commands.
Accessible via `e4s-cl profile <command>`.
"""

from e4s_cl.cli.cli_view import RootCommand
from e4s_cl.model.profile import Profile

HELP_PAGE = """
E4S Container Launcher Profile commands:
"""

COMMAND = RootCommand(Profile,
                      __name__,
                      group="configuration",
                      help_page_fmt=HELP_PAGE)
