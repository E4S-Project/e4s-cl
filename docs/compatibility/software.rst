Software Compatibility
=======================

Container backends
-------------------

As of now, `singularity <https://sylabs.io/docs>`_, `shifter <https://docs.nersc.gov/development/shifter>`_, `docker <https://www.docker.com>`_ and `podman <https://podman.io/>`_ are supported in **e4s-cl**.

More container technologies can be supported. Create an issue on github or write a dedicated module in :code:`e4s_cl/cf/containers`. Refer to :code:`e4s_cl/cf/containers/__init__.py` for details.

.. warning:: Using **docker** with MPI

   Several MPI implementations expect their processes to inherit opened file descriptors; because of docker's client-daemon architecture, this is not possible. To use docker images with MPI, it is encouraged to used `podman <https://podman.io/>`_.

Process launchers
------------------

The following process managers were successfully tested with **e4s-cl**:

- The stock :code:`mpirun` of multiple MPI distributions;
- LLNL's SLURM using :code:`srun`;
- CRAY's ALPS using :code:`aprun`;
- IBM's JSM using :code:`jsrun`.

Support implies the automatic detection of parameters. If a launcher is not
supported, use the ':code:`--`' syntax to separate launcher and process arguments.

See the launcher support definition in :code:`e4s_cl/cf/launchers` for details.
