"""
This file contains a BASH script template that will get written in the
container. This script is to be the entry-point as it should set the
execution environment and allows for arbitrary code execution (e.g.
library loading)
"""

import os, stat
import tempfile
from e4s_cl import logger
from pathlib import Path

LOGGER = logger.get_logger(__name__)

TEMPLATE = """#!/bin/bash
# Source a user-provided script for convenience
%(source_script)s

# If in debug mode, enable linker debugging from here
%(debugging)s

# Enable the host's libraries for this last command by prepending the
# resulting LD_LIBRARY_PATH
export LD_LIBRARY_PATH=%(library_dir)s${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}

# If a linker has been imported, this line will make sure it is used instead
# of the default. This is of the utmost importance, as libc imports will break
# with non-adapted linkers.
export LD_PRELOAD=%(linker)s${LD_PRELOAD:+:${LD_PRELOAD}}

# Finally run the command, using the imported linker if applicable
%(linker)s %(command)s
"""


class Entrypoint:
    def __init__(self):
        # Command to run in the container
        self.command = []

        # Script to source before running anything
        self.source_script_path = ''

        # Path to a directory where the host libraries were bound
        self.library_dir = ''

        # Path to the imported host linker
        self.linker = ''

    @property
    def command(self):
        return " ".join(self.__command)

    @command.setter
    def command(self, rhs):
        if isinstance(rhs, str):
            self.__command = shlex.split(rhs)
        elif isinstance(rhs, list):
            self.__command = rhs
        else:
            raise InternalError("Invalid format for entrypoint command: %s" %
                                repr(rhs))

    @property
    def source_script(self):
        if self.source_script_path:
            return ". %s" % self.source_script_path
        return ""

    def __str__(self):
        fields = {
            'source_script': self.source_script,
            'command': self.command,
            'library_dir': self.library_dir,
            'linker': self.linker,
            'debugging': "export LD_DEBUG=files" if logger.debug_mode() else ''
        }

        return TEMPLATE % fields

    def setUp(self):
        script = tempfile.NamedTemporaryFile('w', delete=False)
        script.write(str(self))
        script.close()

        os.chmod(script.name, 0o755)

        LOGGER.debug("Running templated script:\n" +
                     "".join('=' for _ in range(80)) + "\n%s\n" % str(self) +
                     "".join('=' for _ in range(80)))

        self.file_name = script.name
        return self.file_name

    def tearDown(self):
        if getattr(self, 'file_name', False):
            os.unlink(self.file_name)
