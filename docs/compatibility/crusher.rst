.. _system_crusher:

Running e4s-cl on Crusher at OLCF
=================================

Available on Crusher is a Slurm-based job facility, the Singularity/Apptainer \
container system and a CRAY-based MPI environment. This page will outline how \
to setup, prepare and run a job using **e4s-cl** on this particular system.

Setting up with a profile
-------------------------

:ref:`Initialize<init>` **e4s-cl** using the :code:`init` command.

Make sure you load a MPI module compatible with the MPICH ABI. On :code:`crusher`, they often are named :code:`cray-mpich-abi/x.y.z`.

The program will run a simple MPI program and observe its execution to determine what libraries it used. Make sure you update the :code:`--launcher_args` option value to something you would use on the system, as these options will be passed to srun when launching the process. Available fields are listed on the `crusher help page <https://docs.olcf.ornl.gov/systems/crusher_quick_start_guide.html#running-jobs>`_.

.. code-block:: bash

   $ e4s-cl init                            \
        --backend singularity               \
        --image $YOURIMAGE                  \
        --launcher srun                     \
        --launcher_args '-n 2 -N 2 ... '    \

Creating an initialization script
---------------------------------

Next, we need to make sure the required libraries will be loaded in the container. In this example, we will load the :code:`trilinos` library module using :code:`spack`.

In a new file :code:`shifter-setup.sh`, write what should be done to load the required modules:

.. code-block:: bash

   # Setup spack
   . /spack/share/spack/setup-env.sh

   # Load trilinos
   spack load --first trilinos

Then link this file to the selected profile:

.. code-block:: bash

   $ e4s-cl profile edit --source $PWD/shifter-setup.sh

Running jobs
------------

You can run a **e4s-cl** job like a regular Slurm job by adding a :code:`e4s-cl` launcher command before the srun directive. This can be done using a job file:

.. code-block:: bash

   $ cat run.job
   #SBATCH -N 2 -t 00:30:00

   e4s-cl srun -n 2 /path/to/executable
   $ sbatch run.job

Or from the command line in an interactive job:

.. code-block:: bash

   $ e4s-cl srun -n 2 -N 2 -t 00:30:00 /path/to/executable
