++++++++
Examples
++++++++

Cheat sheet
----------

Initializing the tool for the available MPI library::

    e4s-cl init

Launch a MPI command in a container::

    e4s-cl launch --image ./image.sif --backend singularity mpirun ./binary

Listing the available profiles::

    e4s-cl profile list

.. _init_override:

Library detection override
--------------------------

Some MPI libraries behave differently according to the user's input, making them very hard for **e4s-cl** to accurately profile on its own. You will have to provide a sample MPI environment for **e4s-cl** to analyze. Let's detail one such example.

The following message will appear when a redundant execution is detected:

.. highlight:: bash
.. code::

    $ e4s-cl init
    The target launcher /usr/bin/mpirun uses a single host by default, which
    may tamper with the library discovery. Consider running `e4s-cl profile
    detect` using mpirun specifying multiple hosts.

To ensure the validity of the generated profile, a launcher command should be given with at least some communication between hosts. To do so, one can compile and then run a sample program using **e4s-cl**. Using a generic MPI library:

.. code::

    $ mpicc program.c -o example
    $ e4s-cl profile detect -p <profile_name> \
        mpirun -hosts <host1>,<host2> ./example

On success, the newly-created profile will be found in the profile list.
