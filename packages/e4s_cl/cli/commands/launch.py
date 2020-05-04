"""Launch command

Definition of arguments and hooks related to the launch command,
launcher detection, profile loading, and subprocess creation.
"""

import os
from pathlib import Path
from argparse import ArgumentTypeError, Namespace
from e4s_cl.cf.launchers import LAUNCHERS, parse_cli
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)

def _argument_profile(string):
    """Argument type callback.
    Asserts the entered string matches a defined profile."""
    profile = Profile.controller().one({'name': string})

    if not profile:
        raise ArgumentTypeError("Profile {} does not exist".format(string))
    return profile

def _argument_path(string):
    """Argument type callback.
    Asserts that the string corresponds to an existing path."""
    return Path(string.strip()).as_posix()

def _argument_path_comma_list(string):
    """Argument type callback.
    Asserts that the string corresponds to a list of existing paths."""
    return [_argument_path(data) for data in string.split(',')]

def _parameters(arguments):
    """Generate compound parameters by merging profile and cli arguments
    The profile's parameters have less priority than the ones specified on
    the command line.
    If no profile is given, try to load the selected one."""
    if type(arguments) == Namespace:
        arguments = vars(arguments)

    parameters = dict(arguments.get('profile', Profile.selected()))

    for attr in ['image', 'backend', 'libraries', 'files']:
        if arguments.get(attr, None):
            parameters.update({attr: arguments[attr]})

    return parameters

def _format_execute(parameters):
    from e4s_cl.cli.commands.execute import COMMAND as execute_cmd
    execute_command = str(execute_cmd).split()

    for attr in ['image', 'backend']:
        if parameters.get(attr, None):
            execute_command += ["--{}".format(attr), parameters[attr]]

    for attr in ['libraries', 'files']:
        if parameters.get(attr, None):
            execute_command += ["--{}".format(attr), ",".join(parameters[attr])]

    return execute_command

class LaunchCommand(AbstractCommand):
    """``launch`` subcommand."""

    def _construct_parser(self):
        usage = "%s [arguments] [launcher] [launcher_arguments] [--] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command, usage=usage, description=self.summary)
        parser.add_argument('--profile',
                            type=_argument_profile,
                            help="Name of the profile to use",
                            default=arguments.SUPPRESS,
                            metavar='profile')
        parser.add_argument('--image',
                            type=_argument_path,
                            help="Container image to use",
                            metavar='image')
        parser.add_argument('--files',
                            type=_argument_path_comma_list,
                            help="Files to bind, comma-separated",
                            metavar='files')
        parser.add_argument('--libraries',
                            type=_argument_path_comma_list,
                            help="Libraries to bind, comma-separated",
                            metavar='libraries')
        parser.add_argument('--backend',
                            help="Container backend to use",
                            metavar='solution')
        parser.add_argument('cmd',
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)
        return parser

    @classmethod
    def parse_launcher_cmd(cls, cmd):
        """Parses a command line to split the launcher command and application commands.
        
        Args:
            cmd (list): Command line.
            
        Returns:
            tuple: (Launcher command, possibly empty list of application commands).
        """ 
        launcher_cmd = []
        if cmd[0] in LAUNCHERS:
            launcher_cmd, cmd = parse_cli(cmd)
        else:
            # If '--' appears in the command then everything before it is a launcher + args 
            # and everything after is the application + args 
            if '--' in cmd:
                idx = cmd.index('--')
                launcher_cmd, cmd = cmd[:idx], cmd[idx+1:]

        # No launcher command, just an application command
        return launcher_cmd, cmd

    def main(self, argv):
        args = self._parse_args(argv)

        if not args.cmd:
            self.parser.error("No command given")

        launcher, program = LaunchCommand.parse_launcher_cmd(args.cmd)
        execute_command = _format_execute(_parameters(args))

        LOGGER.debug(" ".join(launcher + execute_command + program))
        util.create_subprocess_exp(launcher + execute_command + program)
        return EXIT_SUCCESS
    
COMMAND = LaunchCommand(__name__, summary_fmt="Launch a process")
