.. _launch:

**launch** - Run MPI commands
=============================

Run a command in a container supplemented with select host libraries.

Usage
-----

.. highlight:: bash
.. code::

    e4s-cl launch [ OPTIONS ] [ LAUNCHER [ -- ] ] < COMMAND >

Arguments
----------

Positional arguments
^^^^^^^^^^^^^^^^^^^^^

:kbd:`LAUNCHER`
    An MPI launcher binary and arguments. **e4s-cl** is compatible with several launchers and will detect their presence. Optional.

:kbd:`COMMAND`
    The command to run in a container. **Required**.

.. admonition:: MPI launcher detection

        E4S Container Launcher needs to determine the exact arguments of the \
        launcher. Certain launchers may have unique options that **e4s-cl** \
        may not recognize.

        To ensure the arguments are understood correctly, an additional \
        :kbd:`--` can be added between the launcher options and the command.

        See the examples below for an illustration.

Optional arguments
^^^^^^^^^^^^^^^^^^^

The :code:`launch` command accepts several arguments to tune its execution:

--profile	Profile to use for the execution. If unspecified, the selected profile will be used.
--image		Image to use when launching the container. Can be a path or identifier. [needed]_
--backend	Container technology to employ. [needed]_
--libraries	Comma-separated list of libraries to make available at run-time in the container. Optional.
--files		Comma-separated list of files to make accessible in the container. They will be bound in-place in the container. Optional.
--source	Path of a script to source before execution. Optional.
--from		If MPI library translation is needed, specify which family the binary comes from. The following are implemented: :code:`intelmpi`, :code:`openmpi`, :code:`mpich`. Optional. See :ref:`MPI implementations` for details.
-h, --help		    print a help message

.. [needed] This information is required for execution, but can be set by the selected profile and the option can be omitted from the command line.

Description
-----------

.. automodule:: e4s_cl.cli.commands.launch

Examples
---------

A launch command using an explicit profile and an MPI launcher:

.. code::

    e4s-cl launch --profile intel-21 mpirun -np 2 ./ping-pong

A launch command using an explicit profile and an MPI launcher, but a different image than the profile's:

.. code::

    e4s-cl launch --profile intel-21 \
        --image /home/user/ecp.simg \
            mpirun -np 2 ./ping-pong

A launch command with implicit profile making explicit the launcher and command:

.. code::

    e4s-cl launch mpirun -np 2 -ppn 1 -- ./ping-pong

A launch command importing binaries in the container before running a script without profile:

.. code::

    e4s-cl launch --files /bin/strace,/bin/lsof \
        --backend singularity \
        --image ~/Images/ecp.simg \
            ./script.sh

A launch command using a local :code:`mpich` library without profile:

.. code::

   e4s-cl launch --backend singularity \
        --image /home/user/ecp.simg \
        --libraries /spack/opt/[...]/mpich-3.4.1-xyz/lib/libmpi.so.12 \
        --files /usr/share/hwdata/pci.ids \
            mpirun -np 2 ./ping-pong

A implicit launch command (parameters implicitly passed via selected profile):

.. code::

   e4s-cl mpirun -np 2 ./ping-pong
