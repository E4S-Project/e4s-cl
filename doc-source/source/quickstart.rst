Quickstart
-------------

The CLI tool is called **e4s-cl**. It behaves as a supplementary launcher over \
regular MPI commands, but can also manage :ref:`profiles<profile>` containing \
information about a MPI library's dependencies.

To begin using **e4s-cl**, the preferred method is to create a profile for the \
target library. The preferred method to achieve this is by using the \
:ref:`init<init>` or :ref:`profile detect<profile_detect>` commands.
The resulting profile can be inspected and modified using the \
:ref:`profile<profile>` sub-commands.

.. highlight:: bash
.. code::

   $ e4s-cl init
   $ e4s-cl profile list
   == Profile Configurations (/home/user/.local/e4s_cl/user.json) ==========

   +----------+----------------------+---------+-------+-----------+-------+
   | Selected |         Name         | Backend | Image | Libraries | Files |
   +==========+======================+=========+=======+===========+=======+
   |    *     |              default |     N/A |   N/A |     6     |   7   |
   +----------+----------------------+---------+-------+-----------+-------+
   $ e4s-cl profile edit --backend singularity --image ./image.sif


Once a profile has been created, it can be used to launch an MPI command !
The :ref:`profile select<profile_select>` command marks a profile as the \
default. Using the :ref:`launch<launch>` command, the program passed as an \
argument will be launched using the desired library.

.. code::

   $ e4s-cl launch mpirun -np 4 -hosts node1,node2 /path/to/executable

Machine-specific execution
------------------------------

Cori at NERSC with Shifter
===========================

Shifter container backend lacks the file import capabilities Docker and \
Singularity allow, but integrates modules to import MPI libraries.
To use these modules alongside of e4s-cl's, creating a profile with no files \
nor libraries is encouraged.

.. code::
   $ e4s-cl profile create cori --backend shifter --image <Your image>
   $ e4s-cl profile select cori
   $ e4s-cl srun -n X /path/to/executable
