"""
Print a list of all the recorded profiles matching a given pattern, along with a brief description.

Pass option **-s** to print only the names and disable formatting.

.. code::

    $ e4s-cl profile list 
    == Profile Configurations (/home/fdeny/.local/e4s_cl/user.json) ===========

    +----------+---------------+---------+-------+-----------+-------+--------+
    | Selected |     Name      | Backend | Image | Libraries | Files | WI4MPI |
    +==========+===============+=========+=======+===========+=======+========+
    |          |   MPICH_3.4.2 |     N/A |   N/A |    16     |   1   |   No   |
    +----------+---------------+---------+-------+-----------+-------+--------+
    |    *     | OpenMPI_4.1.1 |     N/A |   N/A |    21     |  73   |   No   |
    +----------+---------------+---------+-------+-----------+-------+--------+

    $ e4s-cl profile list MPI
    == Profile Configurations (/home/fdeny/.local/e4s_cl/user.json) =========

    +----------+-------------+---------+-------+-----------+-------+--------+
    | Selected |    Name     | Backend | Image | Libraries | Files | WI4MPI |
    +==========+=============+=========+=======+===========+=======+========+
    |          | MPICH_3.4.2 |     N/A |   N/A |    16     |   1   |   No   |
    +----------+-------------+---------+-------+-----------+-------+--------+
    

    $ e4s-cl profile list -s
    MPICH_3.4.2
    OpenMPI_4.1.1


"""

from typing import List, Dict
from e4s_cl.logger import get_logger
from e4s_cl.cli.cli_view import ListCommand
from e4s_cl.model.profile import Profile
from e4s_cl.config import CONFIGURATION

LOGGER = get_logger(__name__)


def _count(attr):
    return lambda x: len(x.get(attr, []))


def _selected(attr):
    return lambda x: '*' if Profile.selected().get(attr) == x[attr] else ' '


def _wi4mpi():

    def __defined(profile):
        if profile.get('wi4mpi') and profile.get('wi4mpi_options'):
            return "Yes"
        return "No"

    return __defined


DEFINED_DASHBOARD_COLUMNS = [{
    'header': 'Selected',
    'function': _selected('name')
}, {
    'header': 'Name',
    'value': 'name',
    'align': 'r'
}, {
    'header': 'Backend',
    'value': 'backend',
    'align': 'r'
}, {
    'header': 'Image',
    'value': 'image',
    'align': 'r'
}, {
    'header': 'Libraries',
    'function': _count('libraries')
}, {
    'header': 'Files',
    'function': _count('files')
}, {
    'header': 'WI4MPI',
    'function': _wi4mpi()
}]

DEFAULT_COLUMNS = ["selected", "name", "backend", "image"]


def _valid_columns(l: List[str]) -> List[Dict]:
    """
    Return a list of column definitions as requested by the entry list of column names
    """

    def column(name):
        matches = list(
            filter(lambda x: x['header'].lower() == name.lower(),
                   DEFINED_DASHBOARD_COLUMNS))
        if matches:
            return matches[0]

        LOGGER.warning("Configuration error: Unrecognized column name: %s",
                       name)
        return None

    return list(filter(None, map(column, l)))


class ProfileListCommand(ListCommand):
    """
    Abstraction of the ListCommand to define profile specific fields to
    show in the list.
    """

    def __init__(self):
        selected_columns = _valid_columns(DEFAULT_COLUMNS)

        config_columns = _valid_columns(CONFIGURATION.profile_list_columns)
        if config_columns:
            selected_columns = config_columns

        super().__init__(Profile, __name__, dashboard_columns=selected_columns)


COMMAND = ProfileListCommand()
