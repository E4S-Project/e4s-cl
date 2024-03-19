.. _qstart:

===========
Quick start
===========

The CLI tool is called **e4s-cl**. It behaves as a supplementary launcher over \
regular MPI commands, but can also manage :ref:`profiles<profile>` containing \
information about a MPI library's dependencies.

Setting up a profile
----------------------

The preferred way to start using **e4s-cl** is to create a profile for the \
target library. The intended method to achieve this is by using the \
:ref:`init<init>` or :ref:`profile detect<profile_detect>` commands.

.. code::

   $ e4s-cl init
   $ e4s-cl profile list
    == Profile Configurations (/storage/users/fdeny/.local/e4s_cl/user.json) =======
    +----------+---------------+---------+-------+
    | Selected |     Name      | Backend | Image |
    +==========+===============+=========+=======+
    |    *     | MVAPICH@2.3.4 |     N/A |   N/A |
    +----------+---------------+---------+-------+
   $ e4s-cl profile show
    Profile name: MVAPICH@2.3.4
    Container image: Not found
    Container tech: Not found
    Pre-execution script: None
    Wi4MPI installation: None

    Bound libraries:
     - libgfortran.so.5 (/lib64/libgfortran.so.5)
     - libibumad.so.3 (/lib64/libibumad.so.3)
     [...]
     - libmlx5-rdmav34.so (/usr/lib64/libibverbs/libmlx5-rdmav34.so)

    Bound files:
     - /etc/libibverbs.d/mlx5.driver
     [...]
     - /usr/share/hwdata/pci.ids


The resulting profile can be inspected and modified using the \
:ref:`profile<profile>` sub-commands. A typical profile setup \
will involve specifying the backend to use as well as the image \
in which to run the binary:

.. code::

   $ e4s-cl profile edit --backend singularity --image ./image.sif
   $ e4s-cl profile list
    == Profile Configurations (/storage/users/fdeny/.local/e4s_cl/user.json) =======
    ----------+---------------+-------------+-------------+
    | Selected |     Name      |   Backend   |    Image    |
    +==========+===============+=============+=============+
    |    *     | MVAPICH@2.3.4 | singularity | ./image.sif |
    +----------+---------------+-------------+-------------+

.. admonition:: Running e4s-cl barebones

   :code:`e4s-cl` is also able to run binaries directly on the host's environment. To do so, select the :code:`barebones` backend. This usually will only work when the binary was also compiled in the host's environment.

.. code::

   $ e4s-cl profile edit --backend barebones
   $ e4s-cl profile list
    == Profile Configurations (/storage/users/fdeny/.local/e4s_cl/user.json) =======
    ----------+---------------+-------------+-------------+
    | Selected |     Name      |   Backend   |    Image    |
    +==========+===============+=============+=============+
    |    *     | MVAPICH@2.3.4 |  barebones  |     None    |
    +----------+---------------+-------------+-------------+

Running a process
----------------------

Once a profile has been created, it can be used to launch an MPI command!
The :ref:`profile select<profile_select>` command marks a profile as the \
default. Using the :ref:`launch<launch>` command, the program passed as an \
argument will be launched using the desired library.

.. code::

   $ e4s-cl launch mpirun -np 4 -hosts node1,node2 /path/to/executable

When the executable was compiled with an ABI-incompatible MPI from the host's MPI, use \
the :code:`--from` flag to signal to **e4s-cl** to enable translation. For a \
list of MPI families and values to use, refer to the :ref:`MPI implementations` \
section.
