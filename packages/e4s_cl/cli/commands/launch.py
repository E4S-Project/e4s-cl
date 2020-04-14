import os
from e4s_cl import EXIT_SUCCESS, HELP_CONTACT, E4S_CL_SCRIPT
from e4s_cl import logger, util, cli
from e4s_cl.cli import arguments, UnknownCommandError
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.error import ConfigurationError

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)
PROGRAM_LAUNCHERS = {'mpirun': ['-app', '--app', '-configfile'],
                     'mpiexec': ['-app', '--app', '-configfile'],
                     'mpiexec.hydra': ['-app', '--app', '-configfile'],
                     'mpiexec.mpd': ['-app', '--app', '-configfile'],
                     'orterun': ['-app', '--app', '-configfile'],
                     'mpiexec_mpt': [],
                     'ccc_mprun': [],
                     'mpirun_rsh': [],
                     'ibrun': [],
                     'aprun': [],
                     'qsub': [],
                     'srun': ['--multi-prog'],
                     'oshrun': [],
                     'cafrun': []}

class LaunchCommand(AbstractCommand):
    """``help`` subcommand."""

    def _construct_parser(self):
        usage = "%s [arguments] [launcher] [launcher_arguments] [--] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command, usage=usage, description=self.summary)
        parser.add_argument('--profile',
                            help="Program profile to use",
                            metavar='profile',
                            nargs=1)
        parser.add_argument('--image',
                            help="Container image to use",
                            metavar='image',
                            nargs=1)
        parser.add_argument('--files',
                            help="Files to bind, comma-separated",
                            metavar='files',
                            nargs=1)
        parser.add_argument('--libraries',
                            help="Libraries to bind, comma-separated",
                            metavar='libraries',
                            nargs=1)
        parser.add_argument('cmd',
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)
        return parser

    @classmethod
    def _separate_launcher_cmd(cls, cmd):
        """Separate the launcher command and it's arguments from the application command(s) and arguments.
        
        Args:
            cmd (list): Command line.
        
        Returns:
            tuple: (Launcher command, Remainder of command line)
        """
        # If '--' appears in the command then everything before it is a launcher + args 
        # and everything after is the application + args 
        if '--' in cmd:
            idx = cmd.index('--')
            return cmd[:idx], cmd[idx+1:]

        cmd0 = cmd[0]

        if cmd0 in [launcher[0] for launcher in PROGRAM_LAUNCHERS.items()]:
            LOGGER.info("Found launcher {}".format(cmd0))

        # No launcher command, just an application command
        return [], cmd

    @classmethod
    def parse_launcher_cmd(cls, cmd):
        """Parses a command line to split the launcher command and application commands.
        
        Args:
            cmd (list): Command line.
            
        Returns:
            tuple: (Launcher command, possibly empty list of application commands).
        """ 
        launcher_cmd, cmd = cls._separate_launcher_cmd(cmd)
        assert launcher_cmd or cmd
        LOGGER.debug('Launcher: %s', launcher_cmd)
        LOGGER.debug('Remainder: %s', cmd)

        if not launcher_cmd:
            return [], cmd
        if not cmd:
            return launcher_cmd, []
        return launcher_cmd, cmd

    def main(self, argv):
        args = self._parse_args(argv)
        launcher, program = LaunchCommand.parse_launcher_cmd(args.cmd)
        print("{} {} execute {}".format(" ".join(launcher), E4S_CL_SCRIPT, " ".join(program)))
        return EXIT_SUCCESS
    
COMMAND = LaunchCommand(__name__, summary_fmt="Launch a process")
