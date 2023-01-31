Configuration File
=======================

In some cases, the user needs to pass specific parameters in the command line for each call. It may be needed to comply with a system's constraints, or a repeated use of parameters, which can be bothersome to type for every command.
For this reason, it is possible to update a selection of settings through a YAML configuration file, which is going to be read automatically at each call.

Configuration file locations
----------------------------

To have a configuration file be loaded by **e4s-cl**, it must be at one of these locations:

1. A system-wide configuration in :code:`/etc/e4s-cl/e4s-cl.yaml`
2. An installation-centric configuration in :code:`<INSTALLDIR>/e4s-cl.yaml`
3. A user-only configuration in :code:`~/.config/e4s-cl.yaml`

Each level has a higher precedence over the above. You can override a system configuration by creating your own configuration file in the user location and setting the keys to your desired values.

Configuration options
---------------------

The following options can be set in a configuration file:

.. list-table::
   :widths: 10 20 10 10
   :header-rows: 1

   * - Field
     - Description
     - Type
     - Default

   * - :code:`container_directory`
     - The path of the directory to bind `e4s-cl` files in.
     - Character string
     - :code:`/.e4s-cl`

   * - :code:`launcher_options`
     - Command line options to append to the launcher when running a multi-process job.
     - List of string
     - :code:`[]`

   * - :code:`preload_root_libraries`
     - Force preload of bound libraries. Useful if some of the libraries were compiled with RPATHs.
     - Boolean
     - :code:`False`

   * - :code:`disable_ranked_log`
     - Disable generation of log files on a per-rank basis.
     - Boolean
     - :code:`False`

**e4s-cl** will not run if the option value is malformed or its type cannot be understood. Any other key-value pair not supported by **e4s-cl** will be ignored.

Some configuration values can also be enabled on a per-module basis. They will be detailed on those modules' documentation.

Configuration file example
---------------------------

Here is an example YAML configuration file:

.. code ::

   ---
   container_directory: '/newdirectory'
   launcher_options: ['-n', '4']
   singularity:
     options: ['--hostname ', 'new_name']
