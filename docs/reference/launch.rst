.. _launch:

**launch** - Run MPI commands
=============================

Usage
-----

.. highlight:: bash
.. code::

    e4s-cl launch [ OPTIONS ] [ MPI LAUNCHER [ -- ] ] < COMMAND >

Options
-------

The `launch` command accepts several options to tune the outcome of its execution:

--profile	Profile to use for the execution
--image		Path for the image to use when launching the container
--backend	Container technology to employ
--libraries	Comma-separated list of libraries to load at run-time
--files		Comma-separated list of files to make accessible in the container
--source	Path of script to source before execution

.. admonition:: MPI launcher detection

        E4S Container Launcher needs to determine the exact arguments of the \
        launcher. Certain launchers may have unique options that **e4s-cl** \
        may not recognize.

        To ensure the arguments are understood correctly, an additional \
        :kbd:`--` can be added between the launcher options and the command.

        See the examples for an illustration.

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

A launch command with implicit profile making explicit the launcher and launchee:

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
        --libraries /home/user/spack/opt/spack/linux-arch-skylake_avx512/gcc-10.2.0/mpich-3.4.1-yjx3whq2g2mrzrws4xhoxyjt7hl6wvb5/lib/libmpi.so.12 \
        --files /usr/share/hwdata/pci.ids \
            mpirun -np 2 ./ping-pong

A implicit launch command (parameters implicitly passed via selected profile):

.. code::

   e4s-cl mpirun -np 2 ./ping-pong
