Software Compatibility
=======================

**e4s-cl** wraps itself around a MPI command and inserts a container launch before the command is run. This implies an understanding of both the process launcher and the container technology to use. This section details the software **e4s-cl** was developped for and tested with.

Container backends
-------------------

Introduction
+++++++++++++

During a :code:`launch` command, a list of required files will be computed on each target node, and bound to a container spawned on those nodes. Container backends are the container technologies **e4s-cl** is able to use.

:code:`apptainer`, :code:`podman`, :code:`shifter` and :code:`singularity` are supported. The :code:`docker` backend can be enabled by installing **e4s-cl** with the :code:`docker` extra feature.

Most of the container backends have some degree of configuration available to them.
Configuration is done by setting the values in the corresponding section of the configuration file, or by passing a given environment variable.

An option passed in the environment will override the same option set in the configuration file.

:code:`apptainer`
++++++++++++++++++

:code:`apptainer` support is achieved using its command line interface. :code:`apptainer` has to be installed on the system and available for it to be used by **e4s-cl**.

The configuration file section for :code:`apptainer` is :code:`apptainer`.
The available options are:

.. list-table::
   :widths: 10 10 5 5 20
   :header-rows: 1

   * - Configuration variable
     - Environment variable
     - Type
     - Default
     - Description

   * - :code:`executable`
     - :code:`E4S_CL_APPTAINER_EXECUTABLE`
     - String
     - :code:`""`
     - Path to the :code:`apptainer` executable to use.

   * - :code:`options`
     - :code:`E4S_CL_APPTAINER_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the spawned :code:`apptainer` process.

   * - :code:`run_options`
     - :code:`E4S_CL_APPTAINER_EXEC_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the :code:`exec` command of the spawned :code:`apptainer` process.

:code:`docker`
++++++++++++++

.. admonition:: :code:`docker` support

   :code:`docker` support in HPC is limited at best. Due to its architecture, it will most likely not work with your MPI implementation. To enable :code:`docker` support from **e4s-cl**, install with the :code:`docker` extra enabled. 

:code:`docker` support is achieved using the :code:`docker-py` `module <https://github.com/docker/docker-py>`_. The :code:`docker` daemon has to be installed and running on the system to be accessed.

There are no configuration options for the :code:`docker` backend.

.. warning:: Using **docker** with MPI

   Several MPI implementations expect their processes to inherit opened file descriptors; because of docker's client-daemon architecture, this is not possible. To use docker images with MPI, it is encouraged to used :ref:`podman`.

.. _podman:

:code:`podman`
+++++++++++++++

:code:`podman` support is achieved using its command line interface. :code:`podman` has to be installed on the system and available for it to be used by **e4s-cl**.

The configuration file section for :code:`podman` is :code:`podman`.
The available options are:

.. list-table::
   :widths: 10 10 5 5 20
   :header-rows: 1

   * - Configuration variable
     - Environment variable
     - Type
     - Default
     - Description

   * - :code:`executable`
     - :code:`E4S_CL_PODMAN_EXECUTABLE`
     - String
     - :code:`""`
     - Path to the :code:`podman` executable to use.

   * - :code:`options`
     - :code:`E4S_CL_PODMAN_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the spawned :code:`podman` process.

   * - :code:`run_options`
     - :code:`E4S_CL_PODMAN_RUN_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the :code:`run` command of the spawned :code:`podman` process.

:code:`shifter`
++++++++++++++++

The :code:`shifter` container technology is an interesting case, as it offers much of what **e4s-cl** is trying to propose, but in a much more restrictive way. 

.. warning:: :code:`shifter` MPI modules

    Some MPI libraries will be configured as modules for :code:`shifter` and imported automatically. You might not need **e4s-cl** ! Check the configuration file in :code:`/etc/shifter/udiRoot.conf` to see if the MPI library you are trying to use is imported.

.. warning:: Binding files with :code:`shifter`

    :code:`shifter` is the only container backend that does not support binding files to the container.
    :code:`shifter` also forbids binding directories to certain locations, like :code:`/etc`.
    This is circumvented by **e4s-cl** by copying all required libraries in a temporary directory, then binding it to the container. Files are ignored.

The configuration file section for :code:`shifter` is :code:`shifter`.

.. list-table::
   :widths: 10 10 5 5 20
   :header-rows: 1

   * - Configuration variable
     - Environment variable
     - Type
     - Default
     - Description

   * - :code:`executable`
     - :code:`E4S_CL_SHIFTER_EXECUTABLE`
     - String
     - :code:`""`
     - Path to the :code:`shifter` executable to use.

   * - :code:`options`
     - :code:`E4S_CL_SHIFTER_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the spawned :code:`shifter` process.

:code:`singularity`
++++++++++++++++++++

:code:`singularity` support is achieved using its command line interface. :code:`singularity` has to be installed on the system and available for it to be used by **e4s-cl**.

The configuration file section for :code:`singularity` is :code:`singularity`.
The available options are:

.. list-table::
   :widths: 10 10 5 5 20
   :header-rows: 1

   * - Configuration variable
     - Environment variable
     - Type
     - Default
     - Description

   * - :code:`executable`
     - :code:`E4S_CL_SINGULARITY_EXECUTABLE`
     - String
     - :code:`""`
     - Path to the :code:`singularity` executable to use.

   * - :code:`options`
     - :code:`E4S_CL_SINGULARITY_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the spawned :code:`singularity` process.

   * - :code:`run_options`
     - :code:`E4S_CL_SINGULARITY_EXEC_OPTIONS`
     - List
     - :code:`[]`
     - Options to pass to the :code:`exec` command of the spawned :code:`singularity` process.

Other container backends
++++++++++++++++++++++++++

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

Additional options can be configured through the configuration file or the environment:

.. list-table::
   :widths: 10 10 5 5 20
   :header-rows: 1

   * - Configuration variable
     - Environment variable
     - Type
     - Default
     - Description

   * - :code:`launcher_options`
     - :code:`E4S_CL_LAUNCHER_OPTIONS`
     - List
     - :code:`[]`
     - List of options to pass to the launcher
