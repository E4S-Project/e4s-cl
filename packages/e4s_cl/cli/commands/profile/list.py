"""
Print a list of all the recorded profiles matching a given pattern, along with a brief description.

Pass option **-s** to print only the names and disable formatting.

.. code::

    $ e4s-cl profile list s
    == Profile Configurations (/home/user/.local/e4s_cl/user.json) ========

    +----------+--------+---------+-------+-----------+-------+
    | Selected |  Name  | Backend | Image | Libraries | Files |
    +==========+========+=========+=======+===========+=======+
    |          | single |    None |  None |     1     |   0   |
    +----------+--------+---------+-------+-----------+-------+
    |          | sparse |    None |  None |     7     |  71   |
    +----------+--------+---------+-------+-----------+-------+

"""

from e4s_cl.cli.cli_view import ListCommand
from e4s_cl.model.profile import Profile


class ProfileListCommand(ListCommand):
    """
    Abstraction of the ListCommand to define profile specific fields to
    show in the list.
    """
    def __init__(self):
        def _count(attr):
            return lambda x: len(x.get(attr, []))

        def _selected(attr):
            return lambda x: '*' if Profile.selected().get(attr) == x[
                attr] else ' '

        def _wi4mpi():
            def __defined(x):
                if x.get('wi4mpi') and x.get('wi4mpi_options'):
                    return "Yes"
                return "No"

            return __defined

        dashboard_columns = [{
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

        super().__init__(Profile,
                         __name__,
                         dashboard_columns=dashboard_columns)


COMMAND = ProfileListCommand()
