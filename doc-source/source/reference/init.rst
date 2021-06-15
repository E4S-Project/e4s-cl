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

--mpi       path to a MPI installation to use instead of the system default
--source    script to run before execution
--image     identifier for the image to use when launching the container
--backend   container technology to employ

Description
-----------

.. automodule:: e4s_cl.cli.commands.init
