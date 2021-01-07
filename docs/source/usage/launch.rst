.. _launch:

Launch command
==============

Brief
-----

E4S Container Launcher is a accessory launcher to ensure host MPI libraries are used in containers.
It wraps around a valid MPI launch command to work.
The full accepted syntax is::

    e4s-cl launch [OPTIONS] <launcher> [LAUNCHER OPTIONS] <command> [COMMAND OPTIONS]

When a :ref:`profile<profiles>` is selected, options can be omitted as the profile's fields will be implicitly used.
Command line options have precedence over profiles' fields.

Options
-------

The `launch` command accepts several options to tune the outcome of its execution:

**--image**
        identifier for the image to use when launching the container

**--backend**
        container technology to employ

**--libraries**
        comma-separated list of libraries to load at run-time

**--files**
        comma-separated list of files to make accessible in the container

**--profile**
        profile to use for the execution

**--source**
        path of script to source before execution
