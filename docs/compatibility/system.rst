.. _system_compat:

System Compatibility
========================

Some machines were specifically taken into account for **e4s-cl** to work on and \
have profiles tailored for them. They can be downloaded at install time to ease \
the initialisation step.

Installation for targeted systems
------------------------------------

To enable such profiles, use the :code:`E4SCL_TARGETSYSTEM` argument when calling \
:code:`make`, :code:`make all` or :code:`make install` if e4s-cl was previously installed.

.. code-block:: bash

    $ make INSTALLDIR=<prefix> all [E4SCL_TARGETSYSTEM=<system_key>]

Successfully tested systems
----------------------------

The following higlights systems on which **e4s-cl** has been tested and has run.

.. csv-table::
   :file: system.csv

Machine-specific tips
------------------------------

Using Shifter at NERSC
**************************

Shifter container backend lacks the file import capabilities Docker and \
Singularity allow, but it integrates modules to import MPI libraries. To use \
these modules alongside of **e4s-cl**'s, it is encouraged to create a profile \
without files or libraries.

.. code::

   $ e4s-cl profile create cori --backend shifter --image <Your image>
   $ e4s-cl profile select cori
   $ e4s-cl srun -n X /path/to/executable
