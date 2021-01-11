.. E4S Container launcher documentation master file, created by
   sphinx-quickstart on Tue Jan  5 10:17:41 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

E4S Container launcher's documentation
==================================================

E4S Container Launcher is an effort to facilitate the use of MPI applications developped using E4S containers on supercomputers without having to compile a new binary on the host.

Given a combination of an MPI library, a container and a MPI binary, E4S Container Launcher will run the MPI binary in the target container using the MPI library.
This is useful when the binary has been compiled using a different library than the one passed as an argument: as long as the two libraries are `ABI compatible <https://www.mpich.org/abi/>`_, the binary will run under the new environment.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   usage/index
   examples
   authors
