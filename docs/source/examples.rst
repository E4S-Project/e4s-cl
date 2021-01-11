++++++++
Examples
++++++++

Initializing the tool for the system MPI library::

    e4s-cl init

Launch a MPI command in a container::

    e4s-cl launch --image ./image.sif --backend singularity -- mpirun ./binary

Listing the available profiles::

    e4s-cl profile list

Specifying an image to use with the selected profile::

    e4s-cl profile edit --image ~/image.sif

Analysing a MPI library for required files::

    e4s-cl profile detect mpirun ./ping-pong
