.. _system_crusher:

Running e4s-cl on Crusher at OLCF
=================================

Available on Crusher is a Slurm-based job facility, the Singularity/Apptainer \
container system and a CRAY-based MPI environment. This page will outline how \
to setup, prepare and run a job using **e4s-cl** on this particular system.

Setting up with a profile
-------------------------

:ref:`Initialize<init>` **e4s-cl** using the :code:`--system` flag:

.. code-block:: bash

   $ e4s-cl init --system crusher \
        --backend singularity     \
        --image $YOURIMAGE

Setting up manually
-------------------

In order to create a profile for the available libraries on Crusher, an \
exhaustive list of all the files required by that library has to be \
established.

**e4s-cl** can help in this task: the following is an in-depth look at how \
this is achieved.

Profile creation
^^^^^^^^^^^^^^^^

First, :ref:`create a profile<profile_create>`.

.. code-block:: bash

   $ e4s-cl profile create singularity-cray-mpich \
        --backend singularity                     \
        --image $YOURIMAGE

MPI library analysis
^^^^^^^^^^^^^^^^^^^^

Next, compile a sample MPI program using the MPI library you wish to use.
For **e4s-cl** to be able to perform library substitution, the library must \
implement the `MPICH ABI <https://www.mpich.org/abi>`_.

On this particular system, we will use the Cray MPICH ABI MPI library, \
available using the :code:`cray-mpich-abi` module.

.. code-block:: bash

   $ module swap cray-mpich cray-mpich-abi

A compiled binary can then be run using :ref:`profile detect<profile_detect>`.
**e4s-cl** will intercept file access system calls during execution and add \
the requested files and libraries to a given profile.

.. admonition:: Compiling a MPICH ABI binary

    On Crusher, the Cray MPICH ABI library does not have an associated \
    compiler; the Cray MPI compilers will compile MPI binaries for their \
    own proprietary ABI.

    You may compile a binary on another system, or use one of the **e4s-cl** \
    provided sample MPI binaries (located in \
    :code:`$INSTALL/system/precompiled_binaries`) to run with.

.. code-block:: bash

   $ e4s-cl profile --profile singularity-cray-mpich detect \
        srun -n 2 $E4S_CL_INSTALL/system/precompiled_binaries/sample_mpich

Upon successful completion of the above command, the profile can be \
:ref:`shown<profile_show>` to display the results.

.. collapse:: Possible output

   .. code-block:: bash

        $ e4s-cl profile show singularity-cray-mpich
        Profile name: singularity-cray-mpich
        Container image: $YOURIMAGE
        Container tech: singularity
        Pre-execution script: None
        WI4MPI: None
        WI4MPI options: None

        Bound libraries:
         - libfabric.so.1 (/opt/cray/libfabric/1.15.0.0/lib64/libfabric.so.1)
         - libpmi.so.0 (/opt/cray/pe/lib64/libpmi.so.0)
         - libu.so.1 (/opt/cray/pe/lib64/cce/libu.so.1)
         - libpsl.so.5 (/usr/lib64/libpsl.so.5)
         - libnghttp2.so.14 (/usr/lib64/libnghttp2.so.14)
         - libcraymath.so.1 (/opt/cray/pe/lib64/cce/libcraymath.so.1)
         - libfi.so.1 (/opt/cray/pe/lib64/cce/libfi.so.1)
         - libldap_r-2.4.so.2 (/usr/lib64/libldap_r-2.4.so.2)
         - libpmi2.so.0 (/opt/cray/pe/lib64/libpmi2.so.0)
         - libmpi.so.12 (/opt/cray/pe/mpich/8.1.12/ofi/crayclang/10.0/lib-abi-mpich/libmpi.so.12)
         - libsasl2.so.3 (/usr/lib64/libsasl2.so.3)
         - libf.so.1 (/opt/cray/pe/lib64/cce/libf.so.1)
         - libcsup.so.1 (/opt/cray/pe/lib64/cce/libcsup.so.1)
         - liblustreapi.so (/usr/lib64/liblustreapi.so)
         - liblber-2.4.so.2 (/usr/lib64/liblber-2.4.so.2)
         - libcxi.so.1 (/usr/lib64/libcxi.so.1)
         - libssh.so.4 (/usr/lib64/libssh.so.4)
         - libpals.so.0 (/opt/cray/pe/lib64/libpals.so.0)
         - libmodules.so.1 (/opt/cray/pe/lib64/cce/libmodules.so.1)
         - libjson-c.so.3 (/usr/lib64/libjson-c.so.3)
         - libatomic.so.1 (/usr/lib64/libatomic.so.1)
         - libmunge.so.2 (/usr/lib64/libmunge.so.2)
         - libcurl.so.4 (/usr/lib64/libcurl.so.4)

        Bound files:
         - /lib64/librt.so.1
         - /lib64/libpthread.so.0
         - /lib64/libc.so.6
         - /usr/lib64/libgssapi_krb5.so.2
         - /usr/lib64/libpcre.so.1
         - /lib64/libdl.so.2
         - /etc/ssl/openssl.cnf
         - /usr/lib64/libk5crypto.so.3
         - /opt/cray/pe/gcc-libs/libgfortran.so.5
         - /lib64/libresolv.so.2
         - /lib64/libselinux.so.1
         - /lib64/libz.so.1
         - /usr/lib64/libunistring.so.2
         - /etc/hosts
         - /opt/cray/pe/gcc-libs/libstdc++.so.6
         - /usr/lib64/libidn2.so.0
         - /etc/resolv.conf
         - /usr/lib64/libkrb5.so.3
         - /lib64/libm.so.6
         - /usr/lib64/libkeyutils.so.1
         - /etc/host.conf
         - /lib64/libcom_err.so.2
         - /usr/lib64/libkrb5support.so.0
         - /var/spool/slurm/mpi_cray_shasta/106509.1/pmi_attribs
         - /opt/cray/pe/lib64/cce/libquadmath.so.0
         - /var/spool/slurm/mpi_cray_shasta/106509.1/apinfo
         - /usr/lib64/libcrypto.so.1.1
         - /usr/lib64/libssl.so.1.1
         - /opt/cray/pe/gcc-libs/libgcc_s.so.1

Profile cleanup
^^^^^^^^^^^^^^^

While **e4s-cl** is able to list the files opened by the process, its sorting heuristic might fail. Files may also be only relevant to a single execution and be obsolete on subsequent runs.
In the above example, both of these situations occur. To remedy this, the following steps can be taken:

- Re-classify files that point to shared objects as libraries. In this case, multiple shared object files are listed in the :code:`Bound files`.

- Identify the temporary files and remove them. If those files are in a special location, add this location to the folder instead. For instance :code:`/var/spool/slurm/mpi_cray_shasta/106509.1/pmi_attribs` is a temporary file as evidenced by the non-existent folder named :code:`106509.1`, but the :code:`/var/spool/slurm/mpi_cray_shasta` can be added as it exists on the host.

These actions can be taken using :ref:`profile edit<profile_edit>`.

.. collapse:: Example final profile

   .. code-block:: bash

        $ e4s-cl profile show 
        Profile name: singularity-cray-mpich
        Container image: $YOURIMAGE
        Container tech: singularity
        Pre-execution script: None
        WI4MPI: None
        WI4MPI options: None

        Bound libraries:
         - libpals.so.0 (/opt/cray/pe/lib64/libpals.so.0)
         - libjson-c.so.3 (/usr/lib64/libjson-c.so.3)
         - libcxi.so.1 (/usr/lib64/libcxi.so.1)
         - libmpi.so.12 (/opt/cray/pe/mpich/8.1.12/ofi/crayclang/10.0/lib-abi-mpich/libmpi.so.12)
         - libpsl.so.5 (/usr/lib64/libpsl.so.5)
         - libfabric.so.1 (/opt/cray/libfabric/1.15.0.0/lib64/libfabric.so.1)
         - libmodules.so.1 (/opt/cray/pe/lib64/cce/libmodules.so.1)
         - libpmi2.so.0 (/opt/cray/pe/lib64/libpmi2.so.0)
         - libmunge.so.2 (/usr/lib64/libmunge.so.2)
         - libsasl2.so.3 (/usr/lib64/libsasl2.so.3)
         - libcurl.so.4 (/usr/lib64/libcurl.so.4)
         - libatomic.so.1 (/usr/lib64/libatomic.so.1)
         - libpmi.so.0 (/opt/cray/pe/lib64/libpmi.so.0)
         - libcraymath.so.1 (/opt/cray/pe/lib64/cce/libcraymath.so.1)
         - libssh.so.4 (/usr/lib64/libssh.so.4)
         - libnghttp2.so.14 (/usr/lib64/libnghttp2.so.14)
         - libfi.so.1 (/opt/cray/pe/lib64/cce/libfi.so.1)
         - libldap_r-2.4.so.2 (/usr/lib64/libldap_r-2.4.so.2)
         - liblustreapi.so (/usr/lib64/liblustreapi.so)
         - libf.so.1 (/opt/cray/pe/lib64/cce/libf.so.1)
         - libu.so.1 (/opt/cray/pe/lib64/cce/libu.so.1)
         - liblber-2.4.so.2 (/usr/lib64/liblber-2.4.so.2)
         - libcsup.so.1 (/opt/cray/pe/lib64/cce/libcsup.so.1)
         - libkrb5support.so.0 (/usr/lib64/libkrb5support.so.0)
         - libkrb5.so.3 (/usr/lib64/libkrb5.so.3)
         - libgfortran.so.5 (/opt/cray/pe/gcc-libs/libgfortran.so.5)
         - libgssapi_krb5.so.2 (/usr/lib64/libgssapi_krb5.so.2)
         - libresolv.so.2 (/lib64/libresolv.so.2)
         - libkeyutils.so.1 (/usr/lib64/libkeyutils.so.1)
         - libidn2.so.0 (/usr/lib64/libidn2.so.0)
         - libselinux.so.1 (/lib64/libselinux.so.1)
         - libunistring.so.2 (/usr/lib64/libunistring.so.2)
         - libk5crypto.so.3 (/usr/lib64/libk5crypto.so.3)
         - libstdc++.so.6 (/opt/cray/pe/gcc-libs/libstdc++.so.6)
         - libquadmath.so.0 (/opt/cray/pe/lib64/cce/libquadmath.so.0)
         - libcom_err.so.2 (/lib64/libcom_err.so.2)
         - libgcc_s.so.1 (/opt/cray/pe/gcc-libs/libgcc_s.so.1)
         - libm.so.6 (/lib64/libm.so.6)
         - libpthread.so.0 (/lib64/libpthread.so.0)
         - libssl.so.1.1 (/usr/lib64/libssl.so.1.1)
         - libcrypto.so.1.1 (/usr/lib64/libcrypto.so.1.1)
         - libc.so.6 (/lib64/libc.so.6)
         - libdl.so.2 (/lib64/libdl.so.2)
         - libpcre.so.1 (/usr/lib64/libpcre.so.1)
         - librt.so.1 (/lib64/librt.so.1)
         - libz.so.1 (/lib64/libz.so.1)

        Bound files:
         - /etc/resolv.conf
         - /etc/ssl/openssl.cnf
         - /etc/host.conf
         - /var/spool/slurm/mpi_cray_shasta
         - /etc/hosts

Profile selection
^^^^^^^^^^^^^^^^^

Finally, select the profile for convenience:

.. code-block:: bash

   $ e4s-cl profile select singularity-cray-mpich

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

   $ e4s-cl srun -n 2 /path/to/executable
