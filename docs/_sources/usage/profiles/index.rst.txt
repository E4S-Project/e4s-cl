.. _profile:

`profile` - Edit and manage profiles
=====================================

A profile is a recorded collection of fields relating to a specific MPI library.

+-------------+----------------------------------------------------------+
| Field       | Description                                              |
+=============+==========================================================+
| `name`      | A name by which the profile is accessed and invoked      |
+-------------+----------------------------------------------------------+
| `image`     | The path of a container image                            |
+-------------+----------------------------------------------------------+
| `backend`   | Identifier for a technology to launch the container with |
+-------------+----------------------------------------------------------+
| `source`    | Path of a script to source before execution              |
+-------------+----------------------------------------------------------+
| `files`     | List of files to make accessible to the running program  |
+-------------+----------------------------------------------------------+
| `libraries` | List of libraries to overload in the running program     |
+-------------+----------------------------------------------------------+

`e4s-cl` will store profiles for later use during :ref:`launch commands<launch>`.
Profiles are accessed and edited using the `profile` subcommands.

**e4s-cl** [ `OPTIONS` ] **profile** OBJECT { `COMMAND` }

`OBJECT` := { **create** | **copy** | **delete** | **edit** | **list** | **show** | **select** | **unselect** | **detect** | **dump** }

.. toctree::
   :caption: Available commands:
   
   create
   copy
   delete
   edit
   list
   show
   select
   unselect
   detect
   dump 
