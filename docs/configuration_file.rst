Configuration File
=======================

In some cases, the user would like to modify some container settings which are hardcoded into the project. While technically updatable in the command given to **e4s-cl launch**, it can be bothersome to specify modifications in every command.
For this reason, it is possible to update a selection of container settings through a yaml configuration file, which is going to be read automatically at each call.

As of now, only the container directory, which is the directory in the container where files are binded, is updatable through a configuration file. If needed, you can contact the **e4s-cl** team and ask for other fields to be updatable.

Configuration file locations
----------------------------

To have a configuration file be loaded by **e4s-cl**, it must be at one of these locations:

- ~/.config/e4s-cl.yaml
- /etc/e4s-cl/e4s-cl.yaml

Configuration file example
---------------------------

Here is an example yaml configuration file:

.. code ::

   ---
   container directory: '/newdirectory'

