**create** - Create a new profile
=================================

Usage
------

.. code::

    e4s-cl profile create <NAME> [ OPTIONS ]

Options 
--------

--libraries	A comma-separated of libraries to add to the profile
--files		A comma-separated of files to add to the profile
--image		The image to use with the profile
--backend	The container technology to use for the profile's image
--source	Path towards a script to source before execution

Description
------------

Create a new profile with the name passed as the first argument.
Arguments passed to options are directly added to the corresponding field of the newly-created profile.
