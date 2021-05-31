import os
import sys
import traceback
from e4s_cl import EXIT_FAILURE, EXIT_WARNING, E4S_CL_SCRIPT
from e4s_cl import logger

LOGGER = logger.get_logger(__name__)


class Error(Exception):
    """Base class for all errors in E4S Container Launcher.
    
    Attributes:
        value: Some value attached to the error, typically a string but could be anything with a __str__ method.
        hints (list): String hints for the user to help resolve the error.
        show_backtrace (bool): Set to True to include a backtrace in the error message.
        message_fmt (str): Format string for the error message.
    """
    show_backtrace = False

    message_fmt = (
        "An unexpected %(typename)s exception was raised:\n"
        "\n"
        "%(value)s\n"
        "\n"
        "%(backtrace)s\n"
        "This is a bug in E4S Container Launcher.\n"
        "Please raise an issue on Github with the contents of '%(logfile)s'.")

    def __init__(self, value, *hints):
        """Initialize the Error instance.
        
        Args:
            value (str): Message describing the error.
            *hints: Hint messages to help the user resolve this error.
        """
        super(Error, self).__init__()
        self.value = value
        self.hints = list(hints)
        self.message_fields = {'logfile': logger.LOG_FILE}

    @property
    def message(self):
        fields = dict(self.message_fields, value=self.value)
        if not self.hints:
            hints_str = ''
        elif len(self.hints) == 1:
            hints_str = 'Hint: %s\n' % self.hints[0]
        else:
            hints_str = 'Hints:\n  * %s\n' % ('\n  * '.join(self.hints))
        fields['hints'] = hints_str
        return self.message_fmt % fields

    def handle(self, etype, value, tb):
        if self.show_backtrace:
            self.message_fields['backtrace'] = ''.join(
                traceback.format_exception(etype, value, tb)) + '\n'
        self.message_fields['typename'] = etype.__name__
        LOGGER.critical(self.message)
        return EXIT_FAILURE


class InternalError(Error):
    """Indicates that an internal error has occurred, i.e. a bug.
    
    These are bad and really shouldn't happen.
    """
    show_backtrace = True


class ConfigurationError(Error):
    """Indicates that E4S Container Launcher cannot succeed with the given parameters.
    
    This is most commonly caused by user error, e.g the user specifies measurement
    settings that are incompatible with the application.
    """
    message_fmt = (
        "%(value)s\n"
        "\n"
        "%(hints)s\n"
        "Cannot proceed with the given inputs.\n"
        "Please check the configuration for errors or raise an issue on Github."
    )

    def __init__(self, value, *hints):
        """Initialize the Error instance.
        
        Args:
            value (str): Message describing the error.
            *hints: Hint messages to help the user resolve this error.
        """
        if not hints:
            hints = ["Try `%s --help`" % os.path.basename(E4S_CL_SCRIPT)]
        super(ConfigurationError, self).__init__(value, *hints)

    def __str__(self):
        return self.value


class ModelError(InternalError):
    """Indicates an error in model data or the model itself."""
    def __init__(self, model, value):
        """Initialize the error instance.
        
        Args:
            model (Model): Data model.
            value (str): A message describing the error.  
        """
        super(ModelError, self).__init__("%s: %s" % (model.name, value))
        self.model = model


class UniqueAttributeError(ModelError):
    """Indicates that duplicate values were given for a unique attribute."""
    def __init__(self, model, unique):
        """Initialize the error instance.
        
        Args:
            model (Model): Data model.
            unique (dict): Dictionary of unique attributes in the data model.  
        """
        super(UniqueAttributeError, self).__init__(
            model, "A record with one of '%s' already exists" % unique)


class ImmutableRecordError(ConfigurationError):
    """Indicates that a data record cannot be modified."""


class IncompatibleRecordError(ConfigurationError):
    """Indicates that a pair of data records are incompatible."""


class ProfileSelectionError(ConfigurationError):
    """Indicates an error while selecting a profile."""
    def __init__(self, value, *hints):
        from e4s_cl.cli.commands.profile.create import COMMAND as profile_create_cmd
        from e4s_cl.cli.commands.profile.select import COMMAND as profile_select_cmd
        from e4s_cl.cli.commands.profile.list import COMMAND as profile_list_cmd
        if not hints:
            hints = (
                "Use `%s` to create a new profile configuration." %
                profile_create_cmd,
                "Use `%s <profile_name>` to select a profile configuration." %
                profile_select_cmd,
                "Use `%s` to see available profile configurations." %
                profile_list_cmd)
        super(ProfileSelectionError, self).__init__(value, *hints)


def excepthook(etype, value, tb):
    """Exception handler for any uncaught exception (except SystemExit).
    
    Replaces :any:`sys.excepthook`.
    
    Args:
        etype: Exception class.
        value: Exception instance.
        tb: Traceback object.
    """
    if etype == KeyboardInterrupt:
        LOGGER.info('Received keyboard interrupt. Exiting.')
        sys.exit(EXIT_WARNING)
    else:
        backtrace = ''.join(traceback.format_exception(etype, value, tb))
        LOGGER.debug(backtrace)
        try:
            sys.exit(value.handle(etype, value, tb))
        except AttributeError:
            message = Error.message_fmt % {
                'value': value,
                'typename': etype.__name__,
                'logfile': logger.LOG_FILE,
                'backtrace': backtrace
            }
            LOGGER.critical(message)
            sys.exit(EXIT_FAILURE)


sys.excepthook = excepthook
