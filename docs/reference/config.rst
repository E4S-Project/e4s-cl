.. _config:

**config** - Manage configuration
===============================

Query and update configuration values from the command line.

Usage
-----

.. code::

    e4s-cl config <action> [ arguments ]

Actions
-------

:list:
    Print the merged configuration (system + install + user) as YAML.

:get:
    Fetch a single configuration value.

:set:
    Update a configuration value in the user configuration file.

Arguments
---------

:kbd:`key`
    Configuration key to read or update. Keys accept dot or underscore notation
    (for example, :code:`wi4mpi.install_directory` or :code:`wi4mpi_install_directory`).

:kbd:`value`
    Value to set for the key (type-checked against the configuration schema).

Examples
--------

.. code::

    # Print merged configuration
    e4s-cl config list

    # Read a specific value
    e4s-cl config get wi4mpi.install_directory

    # Update user configuration
    e4s-cl config set wi4mpi.install_directory /opt/wi4mpi

Description
-----------

.. automodule:: e4s_cl.cli.commands.config
