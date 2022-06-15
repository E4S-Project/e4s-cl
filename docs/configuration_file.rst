Configuration File
=======================

In some cases, the user needs to pass specific parameters in the command line for each call. It may be needed to comply with a system's constraints, or a repeated use of parameters, which can be bothersome to type for every command.
For this reason, it is possible to update a selection of settings through a yaml configuration file, which is going to be read automatically at each call.

As of now, only two parameters are configurable:

- The container directory, which is the directory in the container where files are binded.
- Launchers options, which allows to pass parameters to the launcher at each call.

If needed, you can contact the **e4s-cl** team and ask for other fields to be updatable.

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
   launcher options: "-n 4"

