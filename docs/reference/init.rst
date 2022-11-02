.. _init:

**init** - Initialize the tool
==============================

This command initializes the E4S Container Launcher by generating a template profile from the environment.

Usage
-----

.. code-block::

    e4s-cl init [--mpi <path>] \
        [--launcher <string>] \
        [--launcher_args <string>] \
        [ OPTIONS ] [ [ LAUNCHER [ -- ] ] COMMAND ]

    or

    e4s-cl init --system <string> [OPTIONS]

Arguments
----------

Positional arguments
^^^^^^^^^^^^^^^^^^^^^

:kbd:`LAUNCHER`
    An MPI launcher binary and arguments. **e4s-cl** is compatible with several launchers and will detect their presence. Optional.

:kbd:`COMMAND`
    The command to run in a container. **Required**.

Common options
^^^^^^^^^^^^^^^

These arguments' values will be directly added to the created profile.

--profile           Name of the profile to create or overwrite
--backend           Container technology to employ
--image             Identifier for the image to use when launching the container
--source            Script to run before execution
--wi4mpi            Path to a Wi4MPI installation to use

MPI analysis options
^^^^^^^^^^^^^^^^^^^^

These arguments influence the analysis. They cannot be used with :code:`--system`

--mpi               Path to a MPI installation to use instead of the system default
--launcher          Process launcher executable to use. Default is :code:`mpirun`.
--launcher_args     Arguments to use with the process launcher.

System option
^^^^^^^^^^^^^^

This argument allows to select a pre-made profile.

--system            System name, will use a matching builtin profile if available

Description
-----------

.. automodule:: e4s_cl.cli.commands.init
