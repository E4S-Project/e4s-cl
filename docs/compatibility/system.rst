.. _system_compat:

System Compatibility
========================

Some machines were specifically taken into account for **e4s-cl** to work on and \
have profiles tailored for them. They can be downloaded at install time to ease \
the initialisation step.

Installation for known systems
------------------------------------

To enable such profiles, use the :code:`E4SCL_TARGETSYSTEM` argument when calling \
:code:`make` or :code:`make install`.

.. code-block:: bash

    $ make INSTALLDIR=<prefix> [E4SCL_TARGETSYSTEM=<system_key>] install

Successfully tested systems
----------------------------

The following higlights systems on which **e4s-cl** has been tested and has run.

.. csv-table::
   :file: system.csv

Machine-specific guides
------------------------------

.. toctree::
   :maxdepth: 1

   perlmutter
