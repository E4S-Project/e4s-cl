E4S Container Launcher's |version| documentation
==================================================

Introduction
------------

E4S Container Launcher is an effort to facilitate the use of MPI applications developed using E4S containers on supercomputers without having to compile a new binary on the host.

Given a combination of an MPI library, a container and a MPI binary, E4S Container Launcher will run the MPI binary in the target container using the MPI library.
This is useful when the binary has been compiled using a different library than the one passed as an argument: as long as the two libraries are `ABI compatible <https://www.mpich.org/abi/>`_, the binary will run under the new environment.

.. toctree::
   :maxdepth: 1
   :hidden:

   quickstart
   installation
   reference/index
   compatibility/software
   compatibility/system
   examples
   authors
