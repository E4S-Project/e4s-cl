.. _qstart:

===========
Quickstart
===========

The CLI tool is called **e4s-cl**. It behaves as a supplementary launcher over \
regular MPI commands, but can also manage :ref:`profiles<profile>` containing \
information about a MPI library's dependencies.

Creating a profile
----------------------

The preferred way to start using **e4s-cl** is to create a profile for the \
target library. The intended method to achieve this is by using the \
:ref:`init<init>` or :ref:`profile detect<profile_detect>` commands.
The resulting profile can be inspected and modified using the \
:ref:`profile<profile>` sub-commands.

.. code::

   $ e4s-cl init
   $ e4s-cl profile list
   == Profile Configurations (/home/user/.local/e4s_cl/user.json) ===========

   +----------+--------------+---------+-------+-----------+-------+--------+
   | Selected |     Name     | Backend | Image | Libraries | Files | WI4MPI |
   +==========+==============+=========+=======+===========+=======+========+
   |    *     |  MPICH_3.4.2 |     N/A |   N/A |     6     |   7   |   No   |
   +----------+--------------+---------+-------+-----------+-------+--------+
   $ e4s-cl profile edit --backend singularity --image ./image.sif


Running a process
----------------------

Once a profile has been created, it can be used to launch an MPI command !
The :ref:`profile select<profile_select>` command marks a profile as the \
default. Using the :ref:`launch<launch>` command, the program passed as an \
argument will be launched using the desired library.

.. code::

   $ e4s-cl launch mpirun -np 4 -hosts node1,node2 /path/to/executable

