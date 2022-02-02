from typing import Optional
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

        # Split the message in multiple segments smaller than MAX_CHARACTERS
        for i in range(0, len(message), max_segment_length):
            data['msg'] = message[i:i + max_segment_length]

            try:
                # Log it with no whitespace
                self.stream.write(json.dumps(data, separators=(',', ':')) + self.terminator)
                self.flush()
            except RecursionError: #what
                raise
            except Exception:
                self.handleError(record)


    @classmethod
    def validate(cls, line: str) -> Optional[dict]:
        """
        Check if the string comes from a JSONHandler
        """
        #TODO assert this method is not too pricey with the try-except
        try:
            # Raises ValueError when line is not in JSON format
            data = json.loads(line)

            # Raises ValueError when line does not present a specific marker
            if not data.get(JSONHandler.identifier):
                raise ValueError
        except ValueError:
            return None
        return data
