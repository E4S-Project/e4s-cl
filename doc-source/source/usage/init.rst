`init` - Initialize the tool
============================

**e4s-cl init** [ `OPTIONS` ]

This command initializes E4S Container Launcher for the system's available MPI library.

During initialization, the available MPI library is parsed and analysed to guess its running requirements.
A :ref:`profile<profile>` is created with the collected results from the analysis, and made accessible for the next :ref:`launch command<launch>`.

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
