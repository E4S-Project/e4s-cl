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

# Extra environment variables (e.g., Wi4MPI path overrides)
%(extra_env)s

# Enable the host's libraries for this last command by prepending the
# resulting LD_LIBRARY_PATH
export LD_LIBRARY_PATH=%(library_dir)s${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}

# Preload select libraries to ensure they are used, even if RPATHs are set in
# guest libraries.
export LD_PRELOAD=%(preload)s${LD_PRELOAD:+:${LD_PRELOAD}}

# Verify the host libraries injected above fully resolve against this
# container's runtime before running anything. Host/container ABI
# mismatches (glibc, ROCm/CUDA runtime version, etc.) otherwise only
# surface as a crash deep inside a library constructor once the real
# command is already running (e.g. mid-job under a multi-rank launcher).
_e4s_cl_verify_libs="%(verify_libraries)s"
if [ -n "$_e4s_cl_verify_libs" ] && command -v ldd >/dev/null 2>&1; then
    _e4s_cl_broken=""
    for _e4s_cl_lib in $_e4s_cl_verify_libs; do
        # Unset LD_DEBUG for this call: in debug mode it is exported above
        # for the real command, but would otherwise make each of these ldd
        # calls dump a full linker trace, blowing up the log.
        _e4s_cl_out=$(LD_DEBUG= ldd -r "$_e4s_cl_lib" 2>&1)
        # Some plugins (e.g. ROCm's librocprofiler-register.so) rely on
        # their loading process resolving an optional symbol lazily; that
        # is expected and must not trip this check.
        _e4s_cl_problems=$(echo "$_e4s_cl_out" | grep -E 'undefined symbol|=> not found' | grep -v -e 'rocprofiler_configure')
        if [ -n "$_e4s_cl_problems" ]; then
            _e4s_cl_broken="${_e4s_cl_broken}${_e4s_cl_lib}:
${_e4s_cl_problems}
"
        fi
    done
    if [ -n "$_e4s_cl_broken" ]; then
        echo "e4s-cl: refusing to launch: host libraries injected into this container have unresolved symbols/dependencies:" >&2
        echo "$_e4s_cl_broken" >&2
        echo "e4s-cl: this usually means a host/container ABI mismatch (glibc, ROCm/CUDA runtime version, etc.), not a missing binding. Check 'e4s-cl profile show' and whether this container image is compatible with the host's accelerator stack." >&2
        exit 1
    fi
fi

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

        # Path to the imported host bash/interpreter
        self.interpreter = None

        # Extra environment variables to export (dict of name -> value)
        self.extra_env = {}

        # Paths (inside the container) of host libraries to check for
        # symbol/dependency resolution before running the command
        self.verify_libraries = []

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
        # The command to run
        command = self.command

        # The following is true when the container libc is being replaced
        if self.linker:
            # In case of an ELF binary, start it with the linker; if the
            # command cannot be identified as a binary, run it through bash
            # with the imported linker to ensure the imported libc is loaded
            if self.__command and is_elf(self.__command[0]):
                rtdl = [self.linker]
            elif self.interpreter:
                rtdl = [self.linker, self.interpreter, '-c']
                command = " ".join(['"', *self.__command, '"'])
            else:
                LOGGER.error(
                    "Running a script or command from path is not "
                    "supported in this configuration: missing interpreter"
                    "(linker: %s)", self.linker)

        # Build extra environment exports
        extra_env_lines = []
        for name, value in self.extra_env.items():
            extra_env_lines.append(f'export {name}="{value}"')
        extra_env_str = '\n'.join(extra_env_lines)

        fields = dict(source_script=self.source_script,
                      command=command,
                      library_dir=pathsep.join(
                          map(str, self.linker_library_path)),
                      linker=' '.join(rtdl),
                      preload=':'.join(preload),
                      extra_env=extra_env_str,
                      verify_libraries=' '.join(
                          map(str, self.verify_libraries)),
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
