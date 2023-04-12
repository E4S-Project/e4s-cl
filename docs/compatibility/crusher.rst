.. _system_crusher:

Running e4s-cl on Crusher at OLCF
=================================

Available on Crusher is a Slurm-based job facility, the Singularity/Apptainer \
container system and a CRAY-based MPI environment. This page will outline how \
to setup, prepare and run a job using **e4s-cl** on this particular system.

Setting up with a profile
-------------------------

:ref:`Initialize<init>` **e4s-cl** using the :code:`init` command.

Make sure you load a MPI module compatible with the MPICH ABI. On :code:`crusher`, they often are named :code:`cray-mpich-abi/*`.

The program will run a simple program using the MPI library and observe its execution to determine what libraries it used. Make sure you update the :code:`--launcher_args` option value to something you would use on the system, as these options will be passed to srun when launching the process. Available fields are listed on the `crusher help page <https://docs.olcf.ornl.gov/systems/crusher_quick_start_guide.html#running-jobs>`_.

.. code-block:: bash

   $ e4s-cl init                                   \
        --backend singularity                      \
        --image <IMAGE PATH>                       \
        --launcher srun                            \
        --launcher_args '-n 2 -N 2 -A<ACCOUNT>'    \

Creating an initialization script - Optional
**********************************************

If you used :code:`spack` in the containerized application, we need to make sure the required libraries will be loaded in the container. In this example, we will load the :code:`trilinos` library module using :code:`spack`.

In a new file :code:`crusher-setup.sh`, write what should be done to load the required modules:

.. code-block:: bash

   # Setup spack
   . /spack/share/spack/setup-env.sh

   # Load trilinos
   spack load --first trilinos

Then link this file to the selected profile:

.. code-block:: bash

   $ e4s-cl profile edit --source $PWD/crusher-setup.sh

The file will now be executed in the container before running the application.

Running jobs
------------

You can run a **e4s-cl** job like a regular Slurm job by adding a :code:`e4s-cl` launcher command before the srun directive. This can be done using a job file:

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

Example
----------

The above was used to run OpenFOAM compiled with OpenMPI on Crusher:

.. code-block:: bash

    $ e4s-cl --from openmpi srun -N 4 -A CSC439_crusher -t 00:05:00 pimpleFoam -parallel
    [+] Using selected profile CRAY_MPICH@8.1.17.7
    srun: job 293665 queued and waiting for resources
    srun: job 293665 has been allocated resources
    /*---------------------------------------------------------------------------*\
      =========                 |
      \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
       \\    /   O peration     | Website:  https://openfoam.org
        \\  /    A nd           | Version:  10
         \\/     M anipulation  |
    \*---------------------------------------------------------------------------*/
    Build  : 10-c4cf895ad8fa
    Exec   : pimpleFoam -parallel
    Date   : Mar 30 2023
    Time   : 19:33:22
    Host   : "crusher148"
    PID    : 75646
    I/O    : uncollated
    Case   : /gpfs/alpine/csc439/scratch/sameer/openfoam/tutorials/channel395_ompi
    nProcs : 4
    Slaves :
    3
    (
    "crusher149.4747"
    "crusher150.100632"
    "crusher151.47263"
    )
    Pstream initialised with:
        floatTransfer      : 0
        nProcsSimpleSum    : 0
        commsType          : nonBlocking
        polling iterations : 0
    sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).
    fileModificationChecking : Monitoring run-time modified files using timeStampMaster (fileModificationSkew 10)
    allowSystemOperations : Allowing user-supplied system call operations
    //                                     * //
    Create time
    Create mesh for time = 0
    PIMPLE: No convergence criteria found
    PIMPLE: Operating solver in transient mode with 1 outer corrector
    PIMPLE: Operating solver in PISO mode
    Reading field p
    Reading field U
    Reading/calculating face flux field phi
    Selecting viscosity model constant
    Selecting turbulence model type LES
    Selecting LES turbulence model WALE
    Selecting LES delta type cubeRootVol
    LES
    ...
    Time = 4s
    smoothSolver:  Solving for Ux, Initial residual = 0.00641122, Final residual = 2.16966e-06, No Iterations 2
    smoothSolver:  Solving for Uy, Initial residual = 0.0713268, Final residual = 1.35708e-06, No Iterations 4
    smoothSolver:  Solving for Uz, Initial residual = 0.111266, Final residual = 1.89937e-06, No Iterations 4
    Pressure gradient source: uncorrected Ubar = 0.133501, pressure gradient = 0.000187995
    GAMG:  Solving for p, Initial residual = 0.868194, Final residual = 0.0515595, No Iterations 2
    time step continuity errors : sum local = 4.64447e-10, global = -7.15927e-20, cumulative = -1.53652e-18
    Pressure gradient source: uncorrected Ubar = 0.133501, pressure gradient = 0.000188085
    GAMG:  Solving for p, Initial residual = 0.856293, Final residual = 4.98191e-07, No Iterations 10
    time step continuity errors : sum local = 4.4541e-15, global = -1.10138e-19, cumulative = -1.64666e-18
    Pressure gradient source: uncorrected Ubar = 0.133501, pressure gradient = 0.000188084
    ExecutionTime = 1.46339 s  ClockTime = 1 s
    Courant Number mean: 0.266861 max: 0.269398
    Time = 4.2s
    ...
    Courant Number mean: 0.266973 max: 0.275591
    Time = 39.8s
    smoothSolver:  Solving for Ux, Initial residual = 0.000573163, Final residual = 5.70821e-06, No Iterations 1
    smoothSolver:  Solving for Uy, Initial residual = 0.0767287, Final residual = 7.77675e-06, No Iterations 3
    smoothSolver:  Solving for Uz, Initial residual = 0.059594, Final residual = 4.51633e-06, No Iterations 3
    Pressure gradient source: uncorrected Ubar = 0.1335, pressure gradient = 5.61583e-05
    GAMG:  Solving for p, Initial residual = 0.671047, Final residual = 0.0239423, No Iterations 2
    time step continuity errors : sum local = 9.90873e-10, global = -2.89822e-18, cumulative = -3.76098e-16
    Pressure gradient source: uncorrected Ubar = 0.1335, pressure gradient = 5.64653e-05
    GAMG:  Solving for p, Initial residual = 0.648425, Final residual = 8.52101e-07, No Iterations 9
    time step continuity errors : sum local = 3.61959e-14, global = -2.84365e-18, cumulative = -3.78942e-16
    Pressure gradient source: uncorrected Ubar = 0.1335, pressure gradient = 5.64587e-05
    ExecutionTime = 12.7823 s  ClockTime = 13 s
    Courant Number mean: 0.266973 max: 0.275614
    Time = 40s
    smoothSolver:  Solving for Ux, Initial residual = 0.000570409, Final residual = 5.68148e-06, No Iterations 1
    smoothSolver:  Solving for Uy, Initial residual = 0.076615, Final residual = 7.53652e-06, No Iterations 3
    #!/bin/bash
    smoothSolver:  Solving for Uz, Initial residual = 0.0592336, Final residual = 4.46852e-06, No Iterations 3
    Pressure gradient source: uncorrected Ubar = 0.1335, pressure gradient = 5.60231e-05
    GAMG:  Solving for p, Initial residual = 0.668119, Final residual = 0.0237955, No Iterations 2
    time step continuity errors : sum local = 9.8623e-10, global = -2.94168e-18, cumulative = -3.81884e-16
    Pressure gradient source: uncorrected Ubar = 0.1335, pressure gradient = 5.63292e-05
    #!/bin/bash
    GAMG:  Solving for p, Initial residual = 0.644923, Final residual = 8.53502e-07, No Iterations 9
    time step continuity errors : sum local = 3.63622e-14, global = -2.91724e-18, cumulative = -3.84801e-16
    Pressure gradient source: uncorrected Ubar = 0.1335, pressure gradient = 5.63227e-05
    ExecutionTime = 12.9608 s  ClockTime = 13 s
    End
    Finalising parallel run
