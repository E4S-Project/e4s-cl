import os
import socket
import logging
import json


class JSONHandler(logging.StreamHandler):
    """
    Class emitting record as a JSON object on stdout
    """

    identifier = 'JSON_FORMATTED_RECORD'

    def emit(self, record):
        try:
            template = {
                'level': record.levelname.lower(),
                'process': os.getpid(),
                'host': socket.gethostname(),
                'date': record.created,
                'message': record.getMessage().strip(),
                self.identifier: 1
            }

            message = json.dumps(template)
            stream = self.stream

            stream.write(message + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
