.. _system_perlmutter:

Running e4s-cl on Perlmutter
==============================

Perlmutter at NERSC uses Slurm and Shifter, along with the Cray MPI environment. A profile exists for this system, and this page will highlight how to start from scratch.

The Shifter container system
------------------------------

Shifter (developped by NERSC) uses images stored on a central server.

Contrary to other container solutions, Shifter only binds directories to the guest filesystem. This implies that all the required files need to be copied over to a directory, and some file bindings may not be allowed inside the container.

Fortunately, the program allows for modules that bind and loads libraries installed by the system administrators. There is one such module for MPICH on the system, and we will use it inside the container.

Setting up
-------------

:ref:`Create a profile<profile_create>` for the execution.

.. code-block:: bash

   $ e4s-cl profile create shifter-mpich \
        --backend shifter
        --image $YOURIMAGE

No need to specify files or libraries, as the shifter module will take over from there.

What will be required is a directive to load libraries in the container. In this example, we will load the :code:`trilinos` library module using :code:`spack`.

In a new file :code:`shifter-setup.sh`, write what should be done to load the required modules:

.. code-block:: bash

   # Setup spack
   . /spack/share/spack/setup-env.sh

   # Load trilinos
   spack load --first trilinos

Then link this file to the above profile:

.. code-block:: bash

   $ e4s-cl profile edit shifter-mpich --source $PWD/shifter-setup.sh

Finally, select the profile for convenience:

.. code-block:: bash

   $ e4s-cl profile select shifter-mpich

Running jobs
-----------------

Run a job like a regular Slurm job, but adding a :code:`e4s-cl` launcher directive before it. This can be done using a job file:

.. code-block:: bash

   $ cat run.job
   #SBATCH -N 2 -t 00:30:00

   e4s-cl srun -n 2 /path/to/executable
   $ sbatch run.job

Or from the command line in an interactive job:

.. code-block:: bash

   $ e4s-cl srun -n 2 /path/to/executable
