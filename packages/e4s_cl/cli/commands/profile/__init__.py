from e4s_cl.cli.cli_view import RootCommand
from e4s_cl.model.profile import Profile

HELP_PAGE = """
TAU Commander Profile commands:
"""

COMMAND = RootCommand(Profile, __name__, group="configuration", help_page_fmt=HELP_PAGE)
