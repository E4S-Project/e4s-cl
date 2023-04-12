.. _init:

**init** - Initialize the tool
==============================

This command initializes the E4S Container Launcher by generating a profile for the first MPI library found in the environment.

Usage
-----

.. code-block::

    e4s-cl init [ OPTIONS ] [ COMMAND ]

Arguments
----------

Positional arguments
^^^^^^^^^^^^^^^^^^^^^

:kbd:`COMMAND`
    The MPI command to analyze instead of the default values. You can use a launcher and arguments here. This is needed if the binaries the library produces are non-standard. **Optional**.

Common options
^^^^^^^^^^^^^^^

These arguments' values will be directly added to the created profile.

--profile           Name of the profile to create or overwrite
--backend           Container technology to use for this profile
--image             Identifier for the image to use when launching the container
--source            Script to run in the container before execution
--wi4mpi            Path to a Wi4MPI installation to use for this profile

MPI analysis options
^^^^^^^^^^^^^^^^^^^^

These arguments influence the analysis.

--mpi               Path to a MPI installation to use for this profile
--launcher          Process launcher executable to use; default is :code:`mpirun`
--launcher_args     Arguments to use with the process launcher

Description
-----------

.. automodule:: e4s_cl.cli.commands.init
