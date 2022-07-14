"""
This file contains a BASH script template that will get written in the
container. This script is to be the entry-point as it should set the
execution environment and allows for arbitrary code execution (e.g.
library loading)
"""

from os import chmod, unlink, pathsep
from tempfile import NamedTemporaryFile
from shlex import split
from sotools import is_elf
from e4s_cl import logger
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)

TEMPLATE = """#!/bin/bash
# Source a user-provided script for convenience
%(source_script)s

# If in debug mode, enable linker debugging from here
%(debugging)s

# Enable the host's libraries for this last command by prepending the
# resulting LD_LIBRARY_PATH
export LD_LIBRARY_PATH=%(library_dir)s${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}

# Preload select libraries to ensure they are used, even if RPATHs are set in
# guest libraries.
export LD_PRELOAD=%(preload)s${LD_PRELOAD:+:${LD_PRELOAD}}

# Finally run the command, using the imported linker if applicable
%(linker)s %(command)s
"""


class Entrypoint:
    """
    Objects with exection information that convert to scripts on command
    """

    @property
    def library_dir(self):
        raise NotImplementedError("Deprecated attribute")

    def __init__(self, debug=False):
        self.file_name = None

        # Command to run in the container
        self.command = []

        # Script to source before running anything
        self.source_script_path = ''

        # Directories to add to the runtime linker search path, will take
        # precedence over any paths set before and in the source script
        self.linker_library_path = []

        # List of libraries to preload
        self.preload = []

        # Path to the imported host linker
        self.linker = None

        self.debug = debug

    @property
    def command(self):
        return " ".join(self.__command)

    @command.setter
    def command(self, rhs):
        if isinstance(rhs, str):
            self.__command = split(rhs)
        elif isinstance(rhs, list):
            self.__command = rhs
        else:
            raise InternalError(
                f"Invalid format for entrypoint command: {repr(rhs)}")

    @property
    def source_script(self):
        if self.source_script_path:
            return f". {self.source_script_path}"
        return ""

    def __str__(self):
        # Convert to a set to remove duplicates, then as a list to get order
        preload = list(dict.fromkeys(self.preload))

        # The linker statement to prefix to the command
        rtdl = []
        if self.linker:
            # In case of an ELF binary, start it with the linker; if the
            # command is a script, run bash with the linker to ensure the
            # imported libc is loaded
            if len(self.__command) and is_elf(self.__command[0]):
                rtdl = [self.linker]
            else:
                rtdl = [self.linker, '/.e4s-cl/hostlibs/bash']

        fields = dict(source_script=self.source_script,
                      command=self.command,
                      library_dir=pathsep.join(
                          map(str, self.linker_library_path)),
                      linker=' '.join(rtdl),
                      preload=':'.join(preload),
                      debugging="export LD_DEBUG=files" if self.debug else '')

        return TEMPLATE % fields

    def setup(self):
        """
        Create a temporary file and print the script in it
        """
        with NamedTemporaryFile('w', delete=False) as script:
            self.file_name = script.name
            script.write(str(self))

        chmod(self.file_name, 0o755)

        sep = "\n" + "".join('=' for _ in range(80))
        LOGGER.debug("Running templated script:%(sep)s\n%(script)s%(sep)s", {
            'sep': sep,
            'script': str(self)
        })

        return self.file_name

    def teardown(self):
        if getattr(self, 'file_name', False):
            unlink(self.file_name)
