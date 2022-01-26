Specific machines
=================

Installation
-------------

.. code-block:: bash

    $ make INSTALLDIR=<prefix> install [SYSTEM=<machine_name>]

Some machines were specifically taken into account for **e4s-cl** to work on and have profiles tailored \
for them. They can be downloaded \
at install time to ease the initialisation step.

To enable such profiles, use the :code:`SYSTEM` argument when calling \
:code:`make` or :code:`make install`.

The supported systems are the following:

* Theta at ALCF. Use machine name :code:`theta`;
* Spock at ORNL. Use machine name :code:`spock`;
* Cori at NERSC. Use machine name :code:`cori`;
* Perlmutter at NERSC. Use machine name :code:`perlmutter`.
  

Machine-specific execution
------------------------------

Cori at NERSC with Shifter
**************************

Shifter container backend lacks the file import capabilities Docker and \
Singularity allow, but it integrates modules to import MPI libraries.
To use these modules alongside of e4s-cl's, it is encouraged to create a profile without files \
nor libraries.

.. code::

   $ e4s-cl profile create cori --backend shifter --image <Your image>
   $ e4s-cl profile select cori
   $ e4s-cl srun -n X /path/to/executable
