.. _system_perlmutter:

Running e4s-cl on Perlmutter at NERSC
=====================================

Perlmutter at NERSC uses Slurm and Shifter, along with the Cray MPI environment. A profile exists for this system, and this page will highlight how to start using a profile and how to start from scratch.

The Shifter container system
----------------------------

Contrary to other container solutions, Shifter only binds directories to the guest filesystem. This implies that all the required files need to be copied over to a directory, and some file bindings may not be allowed inside the container.

Fortunately, the program allows for modules that bind and loads libraries installed by the system administrators. There is one such module for MPICH on the system, and we will use it inside the container.

Setting up with a profile
-------------------------

:ref:`Initialize<init>` :code:`e4s-cl` using the :code:`init` command.

Make sure you load a MPI module compatible with the MPICH ABI. On :code:`perlmutter`, they often are named :code:`cray-mpich-abi/*`.

The program will run a simple program using the MPI library and observe its execution to determine what libraries it used. Make sure you update the :code:`--launcher_args` option value to something you would use on the system, as these options will be passed to srun when launching the process. Available fields are listed on the `perlumtter help page <https://docs.nersc.gov/systems/perlmutter/#running-jobs>`_.

.. code-block:: bash

   $ e4s-cl init                                   \
        --backend shifter                          \
        --image <IMAGE ID>                         \
        --launcher srun                            \
        --launcher_args '-n 2 -N 2 -A<ACCOUNT>'    \

Creating an initialization script - Optional
**********************************************

If you used :code:`spack` in the containerized application, we need to make sure the required libraries will be loaded in the container. In this example, we will load the :code:`trilinos` library module using :code:`spack`.

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

Run the job like a regular Slurm job while adding a :code:`e4s-cl` launcher before it. This can be done using a job file:

.. code-block:: bash

   $ cat run.job
   #SBATCH -N 2 -t 00:30:00
   #SBATCH -A <ACCOUNT>

   e4s-cl srun -n 2 <COMMAND>
   $ sbatch run.job

Or from the command line in an interactive job:

.. code-block:: bash

   $ e4s-cl srun -n 2 -N 2 -t 00:30:00 -A<ACCOUNT> <COMMAND>

MPI overloading
********************

Thanks to `CEA's Wi4MPI <https://github.com/cea-hpc/wi4mpi>`_, :code:`e4s-cl` can swap the MPI library at runtime, even allowing to swap OpenMPI and MPICH. This is done by using the `--from` option.

To run a binary compiled using a container's OpenMPI on Perlmutter with the Cray MPICH implementation, follow the above steps the run:

.. code-block:: bash

   $ e4s-cl --from openmpi srun -n 2 -N 2 -t 00:30:00 -A<ACCOUNT> <COMMAND>
