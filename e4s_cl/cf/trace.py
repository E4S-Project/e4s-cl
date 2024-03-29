"""
Use python-ptrace to catch all open and openat system calls, effectively listing
all files accessed by a program
"""


import pathlib
from ptrace.debugger import (PtraceDebugger, ProcessExit, ProcessSignal,
                             NewProcessEvent, ProcessExecution, child)
from ptrace.func_call import FunctionCallOptions
from ptrace.tools import locateProgram
from e4s_cl import logger

LOGGER = logger.get_logger(__name__)


def opened_files(command):
    """
    Use python-ptrace to list open system calls from the command.
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

    return_code = 0

    def list_syscalls():
        # Access the return code above - Python 3 only
        nonlocal return_code
        process.syscall()

        while debugger:
            # Wait until next syscall enter
            try:
                event = debugger.waitSyscall()
            except ProcessExit as event:
                return_code = event.exitcode
                continue
            except ProcessSignal as event:
                event.process.syscall(event.signum)
                continue
            except NewProcessEvent:
                continue
            except ProcessExecution as event:
                print(event)
                continue

            # Process syscall enter or exit
            caught_syscall = event.process.syscall_state.event(FunctionCallOptions())
            if caught_syscall and (caught_syscall.result is not None):
                yield caught_syscall

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
    return return_code, [pathlib.Path(p) for p in paths]
