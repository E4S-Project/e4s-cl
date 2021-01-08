+++++
Usage
+++++

**e4s-cl** [ `OPTIONS` ] OBJECT { `COMMAND` }

`OBJECT` := { **init** | **launch** | **profile** }

`OPTIONS` := { **-V**\[`ersion`] | **-v**\[`erbose`] | **-d**\[`ry-run`] }


E4S Container Launcher requires a subcommand to be given to determine its mode of operation.

The main entrypoint is the :ref:`launch command<launch>`, while the other commands are helpers to facilitate the use of the former.


.. toctree::
   :maxdepth: 1
   :caption: Available commands:

   init
   launch
   profiles/index.rst


Options
--------

**-V**, **--version**
        print the version information of e4s-cl and exit

**-v**, **--verbose**
        print debugging information during execution

**-d**, **--dry-run**
        do nothing; print what would have been done instead
