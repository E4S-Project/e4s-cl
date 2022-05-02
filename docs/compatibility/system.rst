.. _system_compat:

System Compatibility
========================

Some machines were specifically taken into account for **e4s-cl** to work on \
and have profiles tailored for them. They can be downloaded at install time \
to ease the initialisation step.

Installation for known systems
------------------------------------

To enable such profiles, use the :code:`E4SCL_TARGETSYSTEM` argument when \
calling :code:`make` or :code:`make install`. The appropriate profile will be \
downloaded and made available for the installed **e4s-cl** installation.

.. code-block:: bash

    $ make INSTALLDIR=<prefix> E4SCL_TARGETSYSTEM=<system_key> install

Once installed, a builtin profile can be used by passing its name to \
:ref:`e4s-cl init<init>`:

.. code-block:: bash

   $ e4s-cl init --system <system_key> [ ... ]

A list of available builtin profiles can be found in the help page of the \
:ref:`init<init>` command, with the description of the :code:`--system` flag.


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
   crusher
