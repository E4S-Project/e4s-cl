"""
e4s-cl uses launchers to execute code remotely. This forces the passing of
messages to be done on stdout/stderr, so records are serialized to JSON from
the child to be read and logged by the parent.

This model was not supported by the stdlib, as the record fields were protected
from being altered. Notably, the name, lineno, process fields needed to be
updated but the Logger implementation prevented it.

The following lifts those restrictions.
"""

from logging import Logger, _logRecordFactory

class RelayLogger(Logger):
    """
    Logger allowing us to specify internal log fields. This is necessary as
    log records are read from a stream with a delay, and the standard
    implementation prevents setting the created time ourselves.
    """

    # from cpython:Lib/logging/__init__.py:1580 (ddd5f369)
    def makeRecord(self,
                   name,
                   level,
                   fn,
                   lno,
                   msg,
                   args,
                   exc_info,
                   func=None,
                   extra=None,
                   sinfo=None):
        """
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        """
        rv = _logRecordFactory(name, level, fn, lno, msg, args, exc_info, func,
                               sinfo)
        if extra is not None:
            for key in extra:
                rv.__dict__[key] = extra[key]
        return rv



