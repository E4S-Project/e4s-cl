.. _profile_edit:

**edit** - Edit a profile
=========================

Usage
------

.. code::

    e4s-cl profile edit [ NAME ] [ OPTIONS ]

Options
-----------

--name				Change the profile's name
--backend			Change the profile's backend
--image				Change the profile's default image
--source			Change the profile's default init script
--add-files			List of files to add
--remove-files		List of files to remove
--add-libraries		List of libraries to add
--remove-libraries	List of libraries to remove
--wi4mpi			Path of the Wi4MPI installation to use

Description
------------

.. automodule:: e4s_cl.cli.commands.profile.edit
