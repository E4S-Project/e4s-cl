"""
Delete the profile associated with the name passed as an argument.


Delete multiple profiles
-------------------------

You can delete multiple profiles at once by using the '*' wildcard, which will match with any single or multiple characters. 


.. code::

    $ e4s-cl profile list 
    ============================= Profile Configurations (/home/fdeny/.local/e4s_cl/user.json) ==
    +----------+---------------+---------+-------+-----------+-------+--------+
    | Selected |     Name      | Backend | Image | Libraries | Files | WI4MPI |
    +==========+===============+=========+=======+===========+=======+========+
    |    *     |   MPICH_3.4.2 |    None |  None |    16     |   1   |   No   |
    +----------+---------------+---------+-------+-----------+-------+--------+
    |          | MPICH_3.4.2-2 |    None |  None |    16     |   1   |   No   |
    +----------+---------------+---------+-------+-----------+-------+--------+
    |          |   MPICH_3.3.2 |    None |  None |    16     |   1   |   No   |
    +----------+---------------+---------+-------+-----------+-------+--------+
    |          | MPICH_3.3.2-2 |    None |  None |    16     |   1   |   No   |
    +----------+---------------+---------+-------+-----------+-------+--------+

    $ e4s-cl profile delete MPICH_3.*-2 
    Deleted profile 'MPICH_3.4.2-2'
    Deleted profile 'MPICH_3.3.2-2'

    $ e4s-cl profile list
    ============================= Profile Configurations (/home/fdeny/.local/e4s_cl/user.json) ==
    +----------+-------------+---------+-------+-----------+-------+--------+
    | Selected |    Name     | Backend | Image | Libraries | Files | WI4MPI |
    +==========+=============+=========+=======+===========+=======+========+
    |    *     | MPICH_3.4.2 |    None |  None |    16     |   1   |   No   |
    +----------+-------------+---------+-------+-----------+-------+--------+
    |          | MPICH_3.3.2 |    None |  None |    16     |   1   |   No   |
    +----------+-------------+---------+-------+-----------+-------+--------+

"""

from e4s_cl.cli.cli_view import DeleteCommand
from e4s_cl.model.profile import Profile

COMMAND = DeleteCommand(Profile, __name__)
