# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, ParaTools, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# (1) Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
# (2) Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
# (3) Neither the name of ParaTools, Inc. nor the names of its contributors may
#     be used to endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""Utility functions.

Handles system manipulation and status tasks, e.g. subprocess management or file creation.
"""

import os
import re
import sys
import subprocess
import errno
import pkgutil
import pathlib
import hashlib
from collections import deque
from e4s_cl import logger
from e4s_cl.variables import is_master
from e4s_cl.error import InternalError
import termcolor

from ptrace.debugger import (PtraceDebugger, ProcessExit, ProcessSignal,
                             NewProcessEvent, ProcessExecution, child)
from ptrace.func_call import FunctionCallOptions
from ptrace.tools import locateProgram

LOGGER = logger.get_logger(__name__)

# Suppress debugging messages in optimized code
if __debug__:
    _heavy_debug = LOGGER.debug  # pylint: disable=invalid-name
else:

    def _heavy_debug(*args, **kwargs):
        # pylint: disable=unused-argument
        pass


_PY_SUFFEXES = ('.py', '.pyo', '.pyc')

# Don't make this a raw string!  \033 is unicode for '\x1b'.
_COLOR_CONTROL_RE = re.compile('\033\\[([0-9]|3[0-8]|4[0-8])m')


def mkdirp(*args):
    """Creates a directory and all its parents.
    
    Works just like ``mkdir -p``.
    
    Args:
        *args: Paths to create.
    """
    for path in args:
        # Avoid errno.EACCES if a parent directory is not writable and the directory exists
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
                LOGGER.debug("Created directory '%s'", path)
            except OSError as exc:
                # Only raise if another process didn't already create the directory
                if not (exc.errno == errno.EEXIST and os.path.isdir(path)):
                    raise


_WHICH_CACHE = {}


def which(program, use_cached=True):
    """Returns the full path to a program command.

    Program must exist and be executable.
    Searches the system PATH and the current directory.
    Caches the result.

    Args:
        program (str): program to find.
        use_cached (bool): If False then don't use cached results.

    Returns:
        str: Full path to program or None if program can't be found.
    """
    if not program:
        return None
    assert isinstance(program, str)
    if use_cached:
        try:
            return _WHICH_CACHE[program]
        except KeyError:
            pass
    _is_exec = lambda fpath: os.path.isfile(fpath) and os.access(
        fpath, os.X_OK)
    fpath, _ = os.path.split(program)
    if fpath:
        abs_program = os.path.abspath(program)
        if _is_exec(abs_program):
            LOGGER.debug("which(%s) = '%s'", program, abs_program)
            _WHICH_CACHE[program] = abs_program
            return abs_program
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if _is_exec(exe_file):
                LOGGER.debug("which(%s) = '%s'", program, exe_file)
                _WHICH_CACHE[program] = exe_file
                return exe_file
    _heavy_debug("which(%s): command not found", program)
    _WHICH_CACHE[program] = None
    return None


def path_accessible(path, mode='r'):
    """Check if a file or directory exists and is accessible.
    
    Files are checked by attempting to open them with the given mode.
    Directories are checked by testing their access bits only, which may fail for 
    some filesystems which may have permissions semantics beyond the usual POSIX 
    permission-bit model. We'll fix this if it becomes a problem. 
    
    Args:
        path (str): Path to file or directory to check.
        mode (str): File access mode to test, e.g. 'r' or 'rw'
    
    Returns:
        True if the file exists and can be opened in the specified mode, False otherwise.
    """
    assert mode and set(mode) <= set(('r', 'w'))
    if not os.path.exists(path):
        return False
    if os.path.isdir(path):
        modebits = 0
        if 'r' in mode:
            modebits |= os.R_OK
        if 'w' in mode:
            modebits |= os.W_OK | os.X_OK
        return os.access(path, modebits)

    handle = None
    try:
        handle = open(path, mode)
    except IOError as err:
        if err.errno == errno.EACCES:
            return False
        # Some other error, not permissions
        raise
    else:
        return True
    finally:
        if handle:
            handle.close()
    return False


def create_subprocess_exp(cmd, env=None, redirect_stdout=False):
    """Create a subprocess.

    See :any:`subprocess.Popen`.

    Args:
        cmd (list): Command and its command line arguments.
        env (dict): Environment variables to set or unset before launching cmd.
        redirect_stdout (bool): If True return the process' output, 
            instead of passing it to stdtout

    Returns:
        retval: Int Subprocess return code.
        output: String if redirect_stdout is True
    """
    subproc_env = os.environ
    if env:
        for key, val in env.items():
            if val is None:
                subproc_env.pop(key, None)
                _heavy_debug("unset %s", key)
            else:
                subproc_env[key] = val
                _heavy_debug("%s=%s", key, val)

    LOGGER.debug("Creating subprocess: %s", ' '.join(cmd))

    out = (subprocess.PIPE if redirect_stdout else sys.stdout)
    proc = subprocess.Popen(cmd,
                            env=subproc_env,
                            stdout=out,
                            stderr=subprocess.PIPE,
                            close_fds=False,
                            universal_newlines=True)

    output, errors = proc.communicate()
    retval = proc.returncode

    if redirect_stdout:
        LOGGER.debug(output.strip())

    for line in errors.split('\n'):
        # If this is a master process, prettify the output; if not,
        # format it for the master process to understand
        if is_master() and line:
            logger.handle_error(line)
        elif line:
            if retval:
                LOGGER.error(line)
            else:
                LOGGER.warning(line)

    LOGGER.debug("%s returned %d", cmd, retval)

    return retval, output


def create_subprocess(cmd,
                      cwd=None,
                      env=None,
                      stdout=True,
                      log=True,
                      error_buf=50,
                      record_output=False):
    """Create a subprocess.
    
    See :any:`subprocess.Popen`.
    
    Args:
        cmd (list): Command and its command line arguments.
        cwd (str): If not None, change directory to `cwd` before creating the subprocess.
        env (dict): Environment variables to set or unset before launching cmd.
        stdout (bool): If True send subprocess stdout and stderr to this processes' stdout.
        log (bool): If True send subprocess stdout and stderr to the debug log.
        error_buf (int): If non-zero, stdout is not already being sent, and return value is
                          non-zero then send last `error_buf` lines of subprocess stdout and stderr
                          to this processes' stdout.
        record_output (bool): If True return output.
        
    Returns:
        int: Subprocess return code.
    """
    subproc_env = dict(os.environ)
    if env:
        for key, val in env.items():
            if val is None:
                subproc_env.pop(key, None)
                _heavy_debug("unset %s", key)
            else:
                subproc_env[key] = val
                _heavy_debug("%s=%s", key, val)
    LOGGER.debug("Creating subprocess: cmd=%s, cwd='%s'\n", cmd, cwd)
    if error_buf:
        buf = deque(maxlen=error_buf)
    output = []
    proc = subprocess.Popen(cmd,
                            cwd=cwd,
                            env=subproc_env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            close_fds=False,
                            universal_newlines=True,
                            bufsize=1)
    with proc.stdout:
        # Use iter to avoid hidden read-ahead buffer bug in named pipes:
        # http://bugs.python.org/issue3907
        for line in proc.stdout.readlines():
            if log:
                LOGGER.debug(line[:-1])
            if stdout:
                print(line, end='')
            if error_buf:
                buf.append(line)
            if record_output:
                output.append(line)
    proc.wait()

    retval = proc.returncode
    LOGGER.debug("%s returned %d", cmd, retval)

    if retval and error_buf and not stdout:
        for line in buf:
            print(line)

    if record_output:
        return retval, output
    return retval


def get_command_output(cmd):
    """Return the possibly cached output of a command.
    
    Just :any:`subprocess.check_output` with a cache.
    Subprocess stderr is always sent to subprocess stdout.
    
    Args:
        cmd (list): Command and its command line arguments.

    Raises:
        subprocess.CalledProcessError: return code was non-zero.
        
    Returns:
        str: Subprocess output.
    """
    key = repr(cmd)
    try:
        return get_command_output.cache[key]
    except AttributeError:
        get_command_output.cache = {}
    except KeyError:
        pass
    else:
        _heavy_debug("Using cached output for command: %s", cmd)
    LOGGER.debug("Checking subprocess output: %s", cmd)
    stdout = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    get_command_output.cache[key] = stdout
    _heavy_debug(stdout)
    LOGGER.debug("%s returned 0", cmd)
    return stdout


def page_output(output_string):
    """Pipe string to a pager.

    If PAGER is an environment then use that as pager, otherwise
    use `less`.

    Args:
        output_string (str): String to put output.

    """
    if os.environ.get('__E4S_CL_ENABLE_PAGER__', False):
        pager_cmd = os.environ.get('PAGER', 'less -F -R -S -X -K').split(' ')
        proc = subprocess.Popen(pager_cmd, stdin=subprocess.PIPE)
        proc.communicate(bytearray(output_string, 'utf-8'))
    else:
        print(output_string)


def parse_bool(value, additional_true=None, additional_false=None):
    """Parses a value to a boolean value.
    
    If `value` is a string try to interpret it as a bool:
    * ['1', 't', 'y', 'true', 'yes', 'on'] ==> True
    * ['0', 'f', 'n', 'false', 'no', 'off'] ==> False
    Otherwise raise TypeError.
    
    Args:
        value: value to parse to a boolean.
        additional_true (list): optional additional string values that stand for True.
        additional_false (list): optional additional string values that stand for False.
        
    Returns:
        bool: True if  `value` is true, False if `value` is false.
        
    Raises:
        ValueError: `value` does not parse.
    """
    true_values = ['1', 't', 'y', 'true', 'yes', 'on']
    false_values = ['0', 'f', 'n', 'false', 'no', 'off', 'none']
    if additional_true:
        true_values.extend(additional_true)
    if additional_false:
        false_values.extend(additional_false)
    if isinstance(value, str):
        value = value.lower()
        if value in true_values:
            return True
        if value in false_values:
            return False
        raise TypeError
    return bool(value)


def hline(title, *args, **kwargs):
    """Build a colorful horizontal rule for console output.
    
    Uses :any:`logger.LINE_WIDTH` to generate a string of '=' characters
    as wide as the terminal.  `title` is included in the string near the
    left of the horizontal line. 
    
    Args:
        title (str): Text to put on the horizontal rule.
        *args: Positional arguments to pass to :any:`termcolor.colored`.
        **kwargs: Keyword arguments to pass to :any:`termcolor.colored`.
    
    Returns:
        str: The horizontal rule.
    """
    text = "{:=<{}}\n".format('== %s ==' % title, logger.LINE_WIDTH)
    return color_text(text, *args, **kwargs)


def color_text(text, *args, **kwargs):
    """Use :any:`termcolor.colored` to colorize text.
    
    Args:
        text (str): Text to colorize.
        *args: Positional arguments to pass to :any:`termcolor.colored`.
        **kwargs: Keyword arguments to pass to :any:`termcolor.colored`.
        
    Returns:
        str: The colorized text.
    """
    if sys.stdout.isatty():
        return termcolor.colored(text, *args, **kwargs)
    return text


def uncolor_text(text):
    """Remove color control chars from a string.
    
    Args:
        text (str): Text to colorize.
        
    Returns:
        str: The text without control chars.
    """
    return re.sub(_COLOR_CONTROL_RE, '', text)


def walk_packages(path, prefix):
    """Fix :any:`pkgutil.walk_packages` to work with Python zip files.

    Python's default :any:`zipimporter` doesn't provide an `iter_modules` method so
    :any:`pkgutil.walk_packages` silently fails to list modules and packages when
    they are in a zip file.  This implementation works around this.
    """
    def seen(path, dct={}):  # pylint: disable=dangerous-default-value
        if path in dct:
            return True
        dct[path] = True
        return False

    for importer, name, ispkg in _iter_modules(path, prefix):
        yield importer, name, ispkg
        if ispkg:
            __import__(name)
            path = getattr(sys.modules[name], '__path__', None) or []
            path = [p for p in path if not seen(p)]
            for item in walk_packages(path, name + '.'):
                yield item


def _iter_modules(paths, prefix):
    # pylint: disable=no-member
    yielded = {}
    for importer, name, ispkg in pkgutil.iter_modules(path=paths,
                                                      prefix=prefix):
        if name not in yielded:
            yielded[name] = True
            yield importer, name, ispkg


def _parse_line(line):
    """
    Parse single line of ldd output.
    :param line: to parse
    :return: dictionnary with data, or empty if not available
    """
    found = not 'not found' in line
    parts = [part.strip() for part in line.split(' ')]
    # pylint: disable=line-too-long
    # There are two types of outputs for a dependency, with or without soname.
    # For example:
    # with soname: 'libstdc++.so.6 => /usr/lib/x86_64-linux-gnu/libstdc++.so.6 (0x00007f9a19d8a000)'
    # without soname: '/lib64/ld-linux-x86-64.so.2 (0x00007f9a1a329000)'
    # with soname but not found: 'libboost_program_options.so.1.62.0 => not found'
    # with soname but without rpath: 'linux-vdso.so.1 =>  (0x00007ffd7c7fd000)'
    # pylint: enable=line-too-long
    if '=>' in line:
        if len(parts) != 4:
            raise InternalError(
                "Expected 4 parts in the line but found {}: {}".format(
                    len(parts), line))

        soname = None
        dep_path = None
        if found:
            soname = parts[0]
            if parts[2] != '':
                dep_path = pathlib.Path(parts[2])
        else:
            if "/" in parts[0]:
                dep_path = pathlib.Path(parts[0])
            else:
                # No path
                return {}

        return {
            soname: {
                'path': dep_path.as_posix() if dep_path else None,
                'found': found
            }
        }

    if len(parts) != 2:
        raise InternalError(
            "Expected 2 parts in the line but found {}: {}".format(
                len(parts), line))

    if 'ld' in line:
        return {'linker': {'path': parts[0], 'found': True}}

    # In this case, no soname was available
    return {}


def ldd(binary):
    """
    Run ldd on the binary passed as an argument
    """
    binary = pathlib.Path(binary).as_posix()

    command = "%(ldd)s %(binary)s" % {'ldd': which('ldd'), 'binary': binary}

    returncode, output = create_subprocess_exp(command.split(),
                                               redirect_stdout=True)

    if returncode:
        LOGGER.debug("Failed to determine %s's dynamic dependencies", binary)
        return {}

    libraries = {}  # type: Dict
    rows = filter(lambda x: x, [line.strip() for line in output.split('\n')])

    for line in rows:
        libraries.update(_parse_line(line=line))

    return libraries


from e4s_cl.cf.launchers import LAUNCHERS, parse_cli


def interpret_launcher(cmd):
    """Parses a command line to split the launcher command and application commands.

       Args:
           cmd (list[str]): Command line.

       Returns:
           tuple: (Launcher command, possibly empty list of application commands).
       """
    launcher_cmd = []

    # If '--' appears in the command then everything before it is a launcher + args
    # and everything after is the application + args
    if '--' in cmd:
        idx = cmd.index('--')
        launcher_cmd, cmd = cmd[:idx], cmd[idx + 1:]
    elif pathlib.Path(cmd[0]).name in LAUNCHERS:
        launcher_cmd, cmd = parse_cli(cmd)

    env_args = os.environ.get('E4SCL_LAUNCHER_ARGS')

    if launcher_cmd and env_args:
        launcher_cmd += env_args.split(' ')

    # No launcher command, just an application command
    return launcher_cmd, cmd


def opened_files(command):
    """
    Use python-ptrace to list open syscalls from the command.
    """
    files = []
    debugger = PtraceDebugger()
    command[0] = locateProgram(command[0])

    try:
        pid = child.createChild(command, no_stdout=False, close_fds=False)
    except child.ChildError as err:
        LOGGER.error("Failed to list opened files of %s: %s", command[0],
                     str(err))
        return -1, []

    # Debugger.addProcess also uses logging, setting the level to warning
    # mutes info messages
    bkp_level = logger.LOG_LEVEL
    logger.set_log_level('WARNING')
    process = debugger.addProcess(pid, is_attached=True)
    logger.set_log_level(bkp_level)

    returncode = 0

    def list_syscalls():
        # Access the returncode above - Python 3 only
        nonlocal returncode
        process.syscall()

        while debugger:
            # Wait until next syscall enter
            try:
                event = debugger.waitSyscall()
            except ProcessExit as event:
                returncode = event.exitcode
                continue
            except ProcessSignal as event:
                event.process.syscall(event.signum)
                continue
            except NewProcessEvent as event:
                continue
            except ProcessExecution as event:
                print(event)
                continue

            # Process syscall enter or exit
            syscall = event.process.syscall_state.event(FunctionCallOptions())
            if syscall and (syscall.result is not None):
                yield syscall

            # Break at next syscall
            event.process.syscall()

    for syscall in list_syscalls():
        if syscall.result < 0:
            continue
        if syscall.name == "open":
            files.append(syscall.arguments[0].getText())
        if syscall.name == "openat":
            files.append(syscall.arguments[1].getText())

    paths = {name.strip("'") for name in files}
    return returncode, [pathlib.Path(p) for p in paths]


# Dict with the host libraries, with sonames as keys, and paths as values
HOST_LIBRARIES = {}


def host_libraries():
    """
    Output a dict containing all the libraries available on the host,
    under the format {soname: path}
    """
    global HOST_LIBRARIES

    if HOST_LIBRARIES:
        return HOST_LIBRARIES

    _, output = create_subprocess_exp(['ldconfig', '-p'], redirect_stdout=True)

    for row in output.strip().split('\n')[1:]:
        # Expecting format "libname.so.y (lib,arch) => /path/libname.so.y"
        components = row.strip().split(' ')
        HOST_LIBRARIES[components[0]] = components[-1]

    return HOST_LIBRARIES


def flatten(nested_list):
    """Flatten a nested list."""
    return [item for sublist in nested_list for item in sublist]


def extract_libc(text):
    """
    Extract libc version sumber from the output of ldd --version
    We could have used the libc but locating it would require some
    gymnastic, so accessing ldd seemed cleaner.
    """

    # The first line of output is usually:
    # > ldd (<noise with numbers>) x.y
    if not text:
        LOGGER.error("Failed to determine host libc version")
        return (0, 0, 0)

    try:
        version_string = text.split('\n')[0].split()[-1]
    except IndexError:
        LOGGER.error("Failed to determine host libc version")
        return (0, 0, 0)

    return tuple([int(val) for val in re.findall(r'\d+', version_string)])


HOST_LIBC = None


def libc_version():
    global HOST_LIBC

    if HOST_LIBC:
        return HOST_LIBC

    executable = which('ldd')
    ret, out = create_subprocess_exp([executable, '--version'],
                                     redirect_stdout=True)
    if ret:
        LOGGER.error("Could not determine the libc version")
        HOST_LIBC = (0, 0)

    else:
        HOST_LIBC = extract_libc(out)

    return HOST_LIBC


def contains(path1, path2):
    """
    Returns path2 is in the tree of which path1 is the root
    pathlib's < operator compares alphabetically, so here we are
    """
    index = len(path1.parts)
    return path1.parts[:index] == path2.parts[:index]


def unrelative(string):
    """
    Returns a list of all the directories mentionned by a relative path
    """
    path = pathlib.Path(string)
    visited = set()
    deps = set()

    visited.add(path.resolve())
    for i in range(0, len(path.parts)):
        if path.parts[i] == '..':
            visited.add(pathlib.Path(*path.parts[:i]).resolve())

    for element in visited:
        contained = False
        for path in visited:
            if path != element and contains(path, element):
                contained = True

        if not contained:
            deps.add(element)

    return [p.as_posix() for p in deps]


def hash256(string):
    grinder = hashlib.sha256()
    grinder.update(string.encode())
    return grinder.hexdigest()
