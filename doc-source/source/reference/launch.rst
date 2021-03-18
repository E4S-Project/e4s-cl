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

--profile	profile to use for the execution
--image		identifier for the image to use when launching the container
--backend	container technology to employ
--libraries	comma-separated list of libraries to load at run-time
--files		comma-separated list of files to make accessible in the container
--source	path of script to source before execution

Description
-----------

E4S Container Launcher is a accessory launcher to ensure host MPI libraries are used in containers.
It wraps around a valid MPI launch command to work.

The minimal options that must be given are:

* A container image;
* A container technology to run the image with.

When a :ref:`profile<profile>` is selected, options can be omitted as the profile's fields will be implicitly used.
Command line options have precedence over profiles' fields.

E4S Container Launcher will analyze the command line to determine the exact arguments of the launcher.
Certain launchers have esoteric options that may prevent this system from working properly.
To ensure the arguments are understood correctly, an additional `--` can be added between the options and the MPI command.

