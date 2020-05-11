from abc import ABCMeta, abstractmethod
from e4s_cl import logger, cli
from e4s_cl.cli.arguments import ArgumentsNamespace

class AbstractCommand(object, metaclass=ABCMeta):
    """Abstract base class for E4S Container Launcher commands.
    
    Attributes:
        module_name (str): Name of the command module this command object belongs to.
        command (str): Command line string that executes this command.
        summary (str): One-line summary of the command.
        help_page (str): Long and informative description of the command.
        group (str): If not None, commands will be grouped together by group name in help messages.
    """
    
    def __init__(self, module_name, format_fields=None, summary_fmt=None, help_page_fmt=None, group=None):
        if not summary_fmt:
            summary_fmt = "No summary for '%(command)s'"
        if not help_page_fmt:
            help_page_fmt = "No help page for '%(command)s'" 
        self.module_name = module_name
        self.logger = logger.get_logger(module_name)
        self.command = cli.command_from_module_name(module_name)
        self.format_fields = format_fields if format_fields else {}
        self.format_fields['command'] = self.command
        self.summary_fmt = summary_fmt
        self.help_page_fmt = help_page_fmt
        self.group = group
        self._parser = None
        
    def __str__(self):
        return self.command

    @property
    def summary(self):
        return self.summary_fmt % self.format_fields
    
    @property
    def help_page(self):
        return self.help_page_fmt % self.format_fields

    @property
    def parser(self):
        if self._parser is None:
            self._parser = self._construct_parser()
        return self._parser
        
    @property
    def usage(self):
        return self.parser.format_help()

    def _parse_args(self, argv):
        if isinstance(argv, ArgumentsNamespace):
            args = argv
        else:
            args = self.parser.parse_args(args=argv)
        self.logger.debug('%s args: %s', self.command, args)
        return args

    @abstractmethod
    def _construct_parser(self):
        """Construct a command line argument parser."""

    @abstractmethod
    def main(self, argv):
        """Command program entry point.
        
        Args:
            argv (list): Command line arguments.
            
        Returns:
            int: Process return code: non-zero if a problem occurred, 0 otherwise
        """

