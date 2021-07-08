import socket
import logging
import json


class JSONHandler(logging.StreamHandler):
    """
    Class emitting record as a JSON object on a stream
    """

    identifier = 'JSON_FORMATTED_RECORD'

    def emit(self, record):
        try:
            template = {
                'host': socket.gethostname(),
                'name': record.name,
                'levelno': record.levelno,
                'process': record.process,
                'created': record.created,
                # We format the message now to avoid issues converting to JSON
                'msg': record.getMessage(),
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
