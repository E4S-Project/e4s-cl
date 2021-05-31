"""
Dump a json describing the profile, as to transfer it easily between hosts.
"""

from e4s_cl.cli.cli_view import DumpCommand
from e4s_cl.model.profile import Profile


class ProfileDumpCommand(DumpCommand):
    def __init__(self):
        super().__init__(Profile, __name__)


COMMAND = ProfileDumpCommand()
