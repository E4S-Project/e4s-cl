"""
Version helper module
"""

import re
from e4s_cl.error import InternalError


class Version(list):
    """
    Class abstracting a version of form x.y.z.
    Comparison operators are defined for simplicity.
    """
    def __init__(self, string):
        super().__init__()

        digits = re.match(r'.*(?P<version>[0-9]+(\.[0-9]+)+).*', string)

        if digits:
            for digit in digits.group('version').split('.'):
                self.append(int(digit))

    def __str__(self):
        return ".".join([str(digit) for digit in self])

    def __bool__(self):
        return bool(len(self))

    def __gt__(self, rhs):
        if not isinstance(rhs, Version):
            raise InternalError(
                f"Invalid operation > with object of type {type(rhs)}")

        for lhs_d, rhs_d in zip(self, rhs):
            if lhs_d != rhs_d:
                return lhs_d > rhs_d

        return False

    @property
    def major(self):
        return self[0]

    @property
    def minor(self):
        return self[1]

    @property
    def patch(self):
        return self[2]
