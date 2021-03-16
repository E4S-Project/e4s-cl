E4S Container Launcher's documentation
==================================================

Introduction
------------

E4S Container Launcher is an effort to facilitate the use of MPI applications developped using E4S containers on supercomputers without having to compile a new binary on the host.

Given a combination of an MPI library, a container and a MPI binary, E4S Container Launcher will run the MPI binary in the target container using the MPI library.
This is useful when the binary has been compiled using a different library than the one passed as an argument: as long as the two libraries are `ABI compatible <https://www.mpich.org/abi/>`_, the binary will run under the new environment.

Quickstart
----------

The CLI tool is called **e4s-cl**. It behaves as a supplementary launcher over regular MPI commands, but also manages :ref:`profiles<profile>`, that gather information about a MPI library.

To begin using **e4s-cl**, creating one such profile is the easiest method. Ths can be achieved by using the :ref:`init<init>` or :ref:`profile detect<profile_detect>` commands. The resulting profile can be inspected and modified using the :ref:`profile<profile>` subcommands.

Once a profile has been created, it can be used to launch an MPI command ! Using the :ref:`launch<launch>` command, the desired program will be launched using the profile's library.

Commands and examples
---------------------

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   usage/index
   examples
   authors
