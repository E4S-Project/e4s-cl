.. _profile_create:

**create** - Create a new profile
=================================

Usage
------

.. code::

    e4s-cl profile create <NAME> [ OPTIONS ]

Options 
--------

--libraries	A space-separated list of libraries to add to the profile
--files		A space-separated list of files to add to the profile
--image		The image to use with the profile
--backend	The container technology to use for the profile's image
--source	Path towards a script to source before execution
--wi4mpi	Path towards a Wi4MPI installation to use

Description
------------

.. automodule:: e4s_cl.cli.commands.profile.create
