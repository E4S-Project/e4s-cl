.. _init:

**init** - Initialize the tool
==============================

Usage
-----

.. code-block::

    e4s-cl init [ OPTIONS ]

Options
-------

To tailor the initialization process, values can be specified by the user:

--mpi               Path to a MPI installation to use instead of the system default
--source            Script to run before execution
--image             Identifier for the image to use when launching the container
--backend           Container technology to employ
--profile           Profile to create or overwrite
--wi4mpi            Path to a WI4MPI installation to use
--wi4mpi_options    String passed to the underlying WI4MPI launcher
--system            Specific system to download profiles for 

Description
-----------

.. automodule:: e4s_cl.cli.commands.init
