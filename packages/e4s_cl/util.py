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
import time
import atexit
import subprocess
import errno
import shutil
import pkgutil
import tarfile
import tempfile
import hashlib
import pathlib
from collections import deque
from contextlib import contextmanager
from zipfile import ZipFile
import termcolor
from e4s_cl import logger
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)

# Suppress debugging messages in optimized code
if __debug__:
    _heavy_debug = LOGGER.debug  # pylint: disable=invalid-name
else:

    def _heavy_debug(*args, **kwargs):
        # pylint: disable=unused-argument
        pass


_PY_SUFFEXES = ('.py', '.pyo', '.pyc')

_DTEMP_STACK = []

_DTEMP_ERROR_STACK = []

# Don't make this a raw string!  \033 is unicode for '\x1b'.
_COLOR_CONTROL_RE = re.compile('\033\\[([0-9]|3[0-8]|4[0-8])m')


def _cleanup_dtemp():
    if _DTEMP_STACK:
        for path in _DTEMP_STACK:
            if not any(path in paths for paths in _DTEMP_ERROR_STACK):
                rmtree(path, ignore_errors=True)
    if _DTEMP_ERROR_STACK:
        LOGGER.warning(
            'The following temporary directories were not deleted due to build errors: %s.\n',
            ', '.join(_DTEMP_ERROR_STACK))


atexit.register(_cleanup_dtemp)


def calculate_uid(parts):
    """Create a new unique identifier.

    Args:
        parts (list): **Ordered** list of strings to include in the UID calcuation.

    Returns:
        str: A string of hexidecimal digits uniquely calculated from `parts`.
    """
    uid = hashlib.sha1()
    for part in parts:
        uid.update(part)
    digest = uid.hexdigest()
    LOGGER.debug("UID: (%s): %s", digest, parts)
    return digest[:8]


def mkdtemp(*args, **kwargs):
    """Like tempfile.mkdtemp but directory will be recursively deleted when program exits."""
    path = tempfile.mkdtemp(*args, **kwargs)
    _DTEMP_STACK.append(path)
    return path


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


def add_error_stack(path):
    _DTEMP_ERROR_STACK.append(path)


def rmtree(path, ignore_errors=False, onerror=None, attempts=5):
    """Wrapper around shutil.rmtree to work around stale or slow NFS directories.

    Tries repeatedly to recursively remove `path` and sleeps between attempts.

    Args:
        path (str): A directory but not a symbolic link to a directory.
        ignore_errors (bool): If True then errors resulting from failed removals will be ignored.
                              If False or omitted, such errors are handled by calling a handler 
                              specified by `onerror` or, if that is omitted, they raise an exception.
        onerror: Callable that accepts three parameters: function, path, and excinfo.  See :any:shutil.rmtree.
        attempts (int): Number of times to repeat shutil.rmtree before giving up.
    """
    if not os.path.exists(path):
        return None
    for i in range(attempts - 1):
        try:
            return shutil.rmtree(path)
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.warning("Unexpected error: %s", err)
            time.sleep(i + 1)
    shutil.rmtree(path, ignore_errors, onerror)


@contextmanager
def umask(new_mask):
    """Context manager to temporarily set the process umask.
    
    Args:
        new_mask: The argument to :any:`os.umask`.
    """
    old_mask = os.umask(new_mask)
    yield
    os.umask(old_mask)


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


def archive_toplevel(archive):
    """Returns the name of the top-level directory in an archive.
    
    Assumes that the archive file is rooted in a single top-level directory::
        foo
            /bar
            /baz
    
    The top-level directory here is "foo"
    This routine will return stupid results for archives with multiple top-level elements.
    
    Args:
        archive (str): Path to archive file.
        
    Raises:
        IOError: `archive` could not be read.
        
    Returns:
        str: Directory name.
    """
    _heavy_debug("Determining top-level directory name in '%s'", archive)
    try:
        fin = tarfile.open(archive)
    except tarfile.ReadError:
        raise IOError
    else:
        if fin.firstmember.isdir():
            topdir = fin.firstmember.name
        else:
            dirs = [d.name for d in fin.getmembers() if d.isdir()]
            if dirs:
                topdir = min(dirs, key=len)
            else:
                dirs = set()
                names = [d.name for d in fin.getmembers() if d.isfile()]
                for name in names:
                    dirname, basename = os.path.split(name)
                    while dirname:
                        dirname, basename = os.path.split(dirname)
                    dirs.add(basename)
                topdir = min(dirs, key=len)
        LOGGER.debug("Top-level directory in '%s' is '%s'", archive, topdir)
        return topdir


def path_accessible(path, mode='r'):
    """Check if a file or directory exists and is accessable.
    
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


@contextmanager
def _null_context(label):
    yield


DRY_RUN = False


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

    if DRY_RUN:
        print(' '.join(cmd))
        return 0, ""

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
        LOGGER.debug(output)

    if errors:
        if retval != 0:
            LOGGER.error(errors)
        else:
            LOGGER.warning(errors)

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


def human_size(num, suffix='B'):
    """Converts a byte count to human readable units.
    
    Args:
        num (int): Number to convert.
        suffix (str): Unit suffix, e.g. 'B' for bytes.
        
    Returns: 
        str: `num` as a human readable string. 
    """
    if not num:
        num = 0
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


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


def camelcase(name):
    """Converts a string to CamelCase.
    
    Args:
        name (str): String to convert.
        
    Returns:
        str: `name` in CamelCase.
    """
    return ''.join(x.capitalize() for x in name.split('_'))


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

    for importer, name, ispkg in _iter_modules(path, prefix):
        yield importer, name, ispkg
        if ispkg:
            __import__(name)
            path = getattr(sys.modules[name], '__path__', None) or []
            path = [p for p in path if not seen(p)]
            for item in walk_packages(path, name + '.'):
                yield item


def _zipimporter_iter_modules(archive, path):
    """The missing zipimporter.iter_modules method."""
    libdir, _, pkgpath = path.partition(archive + os.sep)
    with ZipFile(os.path.join(libdir, archive)) as zipfile:
        namelist = zipfile.namelist()

    def iter_modules(prefix):
        for fname in namelist:
            fname, ext = os.path.splitext(fname)
            if ext in _PY_SUFFEXES:
                extrapath, _, modname = fname.partition(pkgpath + os.sep)
                if extrapath or modname == '__init__':
                    continue
                pkgname, modname = os.path.split(modname)
                if pkgname:
                    if os.sep in pkgname:
                        continue
                    yield prefix + pkgname, True
                else:
                    yield prefix + modname, False

    return iter_modules


def _iter_modules(paths, prefix):
    # pylint: disable=no-member
    yielded = {}
    for importer, name, ispkg in pkgutil.iter_modules(path=paths,
                                                      prefix=prefix):
        if name not in yielded:
            yielded[name] = True
            yield importer, name, ispkg


def get_binary_linkage(cmd):
    ldd = which('ldd')
    if not ldd:
        return None
    proc = subprocess.Popen([ldd, cmd],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    stdout, _ = proc.communicate()
    if proc.returncode:
        return 'static' if stdout else None
    return 'dynamic'


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

    else:
        if len(parts) != 2:
            raise InternalError(
                "Expected 2 parts in the line but found {}: {}".format(
                    len(parts), line))

        # In this case, no soname was available
        return {}


def _ldd_output_parser(cmd_out):
    """
    Parse the command line output.
    :param cmd_out: command line output
    :return: Dictionnary of dependencies
    """
    dependencies = {}  # type: Dict

    for line in [
            line.strip() for line in cmd_out.split('\n') if line.strip() != ''
    ]:
        dependencies.update(_parse_line(line=line))

    return dependencies


def list_dependencies(path, env=None):
    """
    Retrieve a list of dependencies of the given binary.
    :param path: pathlib.Path: path to a file
    :param env: dict[str, str]: the environment to use
    If ``env`` is None, currently active env will be used.
    Otherwise specified env is used.
    :return: list of dependencies
    """

    # Check if the file is present on the filesystem
    if not path.exists():
        raise InternalError("Failed to ldd external library {}: File does not"
                            "exist".format(path))

    # Add it as a dependency
    deps = {path.name: {"path": path.as_posix(), "found": True}}

    proc = subprocess.Popen(["ldd", path.as_posix()],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            env=env)

    out, err = proc.communicate()

    if proc.returncode != 0:
        raise InternalError(
            "Failed to ldd external libraries of {} with code {}:\nout:\n{}\n\n"
            "err:\n{}".format(path, proc.returncode, out, err))

    deps.update(_ldd_output_parser(cmd_out=out))

    return deps
