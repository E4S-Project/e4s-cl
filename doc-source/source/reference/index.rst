Reference
=========

Usage
-----

**e4s-cl** [ `OPTIONS` ] OBJECT { `COMMAND` }

`OBJECT` := { **init** | **launch** | **profile** }

`OPTIONS` := { **-V**\[`ersion`] | **-v**\[`erbose`] | **-d**\[`ry-run`] }

Options
--------

**-V**, **--version**
        print the version information of **e4s-cl** and exit

**-v**, **--verbose**
        print debugging information during execution

**-d**, **--dry-run**
        do nothing; print what would have been done instead

Description
-------------

This top level command is the entrypoint to the application. Options given here will influence all modes of operation, but the command by itself does not amount to any operation.

Sub-Commands Description
---------------------------

.. toctree::
   :maxdepth: 1

   init
   launch
   profiles/index.rst


