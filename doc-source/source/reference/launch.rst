.. _launch:

**launch** - Run MPI commands
=============================

Usage
-----

.. code::

    e4s-cl launch [ OPTIONS ] [ -- ] < MPI Command >

Options
-------

The `launch` command accepts several options to tune the outcome of its execution:

--profile	Profile to use for the execution
--image		Identifier for the image to use when launching the container
--backend	Container technology to employ
--libraries	List of libraries to load at run-time
--files		List of files to make accessible in the container
--source	Path of script to source before execution

Description
-----------

.. automodule:: e4s_cl.cli.commands.launch
