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

You can also dump multiple profiles at once by specifying multiple profiles:

.. code::
    
    $ e4s-cl profile dump MPICH_3.4.2 MPICH_3.3.2
    [
        {
            "name": "MPICH_3.4.2",
            "libraries": ["/usr/lib/libz.so.1", [...], "/usr/lib/libicuuc.so.70"],
            "files": ["/usr/share/hwdata/pci.ids"],
            "source": null,
            "image": null,
            "wi4mpi_options": null,
            "backend": "None",
            "wi4mpi": null},
        {
            "name": "MPICH_3.3.2",
            "libraries": ["/usr/lib/libm.so.6", [...], "/usr/lib/libc.so.6"],
            "files": ["/usr/share/hwdata/pci.ids"],
            "image": null,
            "source": null,
            "wi4mpi_options": null,
            "wi4mpi": null,
            "backend": null
        }
    ]
"""

from e4s_cl.cli.cli_view import DumpCommand
from e4s_cl.model.profile import Profile


class ProfileDumpCommand(DumpCommand):
    def __init__(self):
        super().__init__(Profile, __name__)


COMMAND = ProfileDumpCommand()
