.. _init:

**init** - Initialize the tool
==============================

This command initializes the E4S Container Launcher by generating a template \
profile from the available environment.

Usage
-----

.. code-block::

    e4s-cl init --system <string> [OPTIONS]

    or

    e4s-cl init --wi4mpi <path> \
        [--wi4mpi_options <string>] \
        [OPTIONS]

    or

    e4s-cl init [--mpi <path>] \
        [--launcher <string>] \
        [--launcher_args <string>] \
        [OPTIONS]

Options
-------

To tailor the initialization process the following values can be specified by \
the user. The options of the system, WI4MPI and MPI analysis groups are \
mutually exclusive.

System initialization options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

--system            System name, will use a matching builtin profile if available

WI4MPI initialization options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

--wi4mpi            Path to a WI4MPI installation to use
--wi4mpi_options    String passed to the underlying WI4MPI launcher

MPI analysis initialization options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

--mpi               Path to a MPI installation to use instead of the system default
--launcher          Process launcher executable to use
--launcher_args     Arguments to use with the process launcher

Common initialization options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

--profile           Name of the profile to create or overwrite
--backend           Container technology to employ
--image             Identifier for the image to use when launching the container
--source            Script to run before execution

Description
-----------

.. automodule:: e4s_cl.cli.commands.init
