"""Launch command

Definition of arguments and hooks related to the launch command,
launcher detection, profile loading, and subprocess creation.
"""

import os
from e4s_cl.cf.launchers import LAUNCHERS, parse_cli
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)

class LaunchCommand(AbstractCommand):
    """``launch`` subcommand."""

    def _construct_parser(self):
        usage = "%s [arguments] [launcher] [launcher_arguments] [--] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command, usage=usage, description=self.summary)
        parser.add_argument('--image',
                            help="Container image to use",
                            metavar='image')
        parser.add_argument('--files',
                            help="Files to bind, comma-separated",
                            metavar='files')
        parser.add_argument('--libraries',
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
        launcher, program = LaunchCommand.parse_launcher_cmd(args.cmd)

        execute_command = [E4S_CL_SCRIPT, 'execute']
        if args.files:
            execute_command += ['--files', args.files]
        if args.libraries:
            execute_command += ['--libraries', args.libraries]
        if args.backend:
            execute_command += ['--backend', args.backend]
        if args.image:
            execute_command += ["--image", args.image]

        LOGGER.debug(" ".join(launcher + execute_command + program))
        util.create_subprocess_exp(launcher + execute_command + program)
        return EXIT_SUCCESS
    
COMMAND = LaunchCommand(__name__, summary_fmt="Launch a process")
