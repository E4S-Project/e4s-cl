**edit** - Edit a profile
=========================

Usage
------

.. code::

    e4s-cl profile edit [ NAME ] [ OPTIONS ]

Options
-----------

--new_name		Change the profile's name
--backend		Change the profile's backend
--image		    Change the profile's default image
--source		Change the profile's default init script
--add-files		Comma-separated list of files to add
--remove-files		Comma-separated list of files to remove
--add-libraries		Comma-separated list of libraries to add
--remove-libraries      Comma-separated list of libraries to remove

Description
------------

Modify the profile associated to the name passed as an argument.

Passing a value to the options **--new_name**, **--backend**, **--image**, **--source** will overwrite the profile's corresponding field.

Passing a value to **--add-files**, **--remove-files**, **--add-libraries**, **--remove-libraries** will add or remove elements from the list of files or libraries, accordingly.

The name argument can be omitted in case a profile is selected, in which case the selected profile is modified.
