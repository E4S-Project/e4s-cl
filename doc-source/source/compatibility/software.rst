Software Compatibility
=======================

Container backends
-------------------

As of now, only `singularity <https://sylabs.io/docs>`_  and `shifter <https://docs.nersc.gov/development/shifter>`_ are supported in **e4s-cl**.

More container technologies can be supported. Create an issue on github or write a dedicated module in :code:`e4s_cl/cf/containers`. Refer to :code:`e4s_cl/cf/containers/__init__.py` for details.

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
