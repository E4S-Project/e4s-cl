"""
Print profile in its internal representation (JSON format).
Used to parse and/or access profiles in an script-accessible way.

If the profile name is omitted, the selected profile will be used.

.. code::

    $ e4s-cl profile dump single
    [
        {
            "name": "single",
            "backend": null,
            "image": null,
            "source": null,
            "files": [],
            "libraries": ["/usr/lib/libmpi.so"]
        }
    ]

"""

from e4s_cl.cli.cli_view import DumpCommand
from e4s_cl.model.profile import Profile


class ProfileDumpCommand(DumpCommand):
    def __init__(self):
        super().__init__(Profile, __name__)


COMMAND = ProfileDumpCommand()
