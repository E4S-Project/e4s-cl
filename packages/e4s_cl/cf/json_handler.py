import socket
import logging
import json

MAX_CHARACTERS = 4096


class JSONHandler(logging.StreamHandler):
    """
    Class emitting record as a JSON object on a stream
    """

    identifier = '__JSONLOG'

    def emit(self, record):
        data = {
            'host': socket.gethostname(),
            'name': record.name,
            'levelno': record.levelno,
            'process': record.process,
            'created': record.created,
            'msg': "",
            self.identifier: 1
        }

        template_length = len(json.dumps(data))
        message = record.getMessage()
        max_segment_length = MAX_CHARACTERS - template_length

        for i in range(0, len(message), max_segment_length):
            data['msg'] = message[i:i + max_segment_length]

            try:
                self.stream.write(json.dumps(data, separators=(',', ':')) + self.terminator)
                self.flush()
            except RecursionError:
                raise
            except Exception:
                self.handleError(record)
