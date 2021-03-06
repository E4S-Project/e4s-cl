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
import json
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


def flatten(nested_list):
    """Flatten a nested list."""
    return [item for sublist in nested_list for item in sublist]


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

    visited.add(path)
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
    """
    Create a hash from a string
    """
    grinder = hashlib.sha256()
    grinder.update(string.encode())
    return grinder.hexdigest()


def JSONSerializer(obj):
    """
    JSON add-on that will transform classes into dicts, and sets into special
    objects to be decoded back into sets with `util.JSONDecoder`.
    """
    if getattr(obj, '__dict__', False):
        return {'__type': type(obj).__name__, '__dict': obj.__dict__}
    if isinstance(obj, set):
        return {'__type': 'set', '__list': list(obj)}

    return obj

"""
Dict of methods to use when decoding e4s-cl json. Keys correspond to values
of the `__type` field.
"""
JSON_HOOKS = {}

def JSONDecoder(obj):
    """
    JSON add-on to decode dicts with embedded data from `util.JSONSerializer`
    """
    if obj.get('__type', False):
        if obj['__type'] == 'set':
            return set(obj['__list'])

        if obj['__type'] in JSON_HOOKS.keys():
            return JSON_HOOKS[obj['__type']](obj['__dict'])

    return obj


def json_dumps(*args, **kwargs):
    """
    json.dumps wrapper
    """
    if kwargs.get('default'):
        raise InternalError("Cannot override default from util.json_dumps")

    kwargs['default'] = JSONSerializer

    return json.dumps(*args, **kwargs)


def json_loads(*args, **kwargs):
    """
    json.loads wrapper
    """
    if kwargs.get('object_hook'):
        raise InternalError("Cannot override object_hook from util.json_loads")

    kwargs['object_hook'] = JSONDecoder

    return json.loads(*args, **kwargs)
