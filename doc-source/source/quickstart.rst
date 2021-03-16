Quickstart
----------

The CLI tool is called **e4s-cl**. It behaves as a supplementary launcher over regular MPI commands, but also manages :ref:`profiles<profile>`, that gather information about a MPI library.

To begin using **e4s-cl**, creating one such profile is the easiest method. Ths can be achieved by using the :ref:`init<init>` or :ref:`profile detect<profile_detect>` commands. The resulting profile can be inspected and modified using the :ref:`profile<profile>` subcommands.

Once a profile has been created, it can be used to launch an MPI command ! Using the :ref:`launch<launch>` command, the desired program will be launched using the profile's library.

