Init command
============

Brief
-----

This command initializes `e4s-cl` for the system's available MPI library.
A profile is created and selected with the findings.

Options
-------

To better control the initialization process, values can be specified by the user:

**--mpi**
        path to a mpi installation to use instead of the system default

**--source**
        script to run before execution

**--image**
        identifier for the image to use when launching the container

**--backend**
        container technology to employ

Examples
--------

To use the system default MPI library::

    e4s-cl init
