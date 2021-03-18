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

This command initializes E4S Container Launcher for the system's available MPI library.

During initialization, the available MPI library is parsed and analyzed to guess its running requirements.
A :ref:`profile<profile>` is created with the collected results from the analysis, and made accessible for the next :ref:`launch command<launch>`.

.. caution::

   The process relies on the good configuration of the MPI launcher, but this may fail.
   A message will appear in case some limitations were detected.
   It is good practice to :ref:`perform this process manually<init_override>` to ensure the network stack is exposed to **e4s-cl**.
