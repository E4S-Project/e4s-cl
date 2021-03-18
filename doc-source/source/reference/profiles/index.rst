.. _profile:

**profile** - Edit and manage profiles
======================================

Usage
-----

.. code::

    e4s-cl [ OPTIONS ] profile SUBCOMMAND { ARGUMENTS }

    SUBCOMMAND := { create | copy | delete | edit | list | show
                           | select | unselect | detect | dump }

Sub-Commands
------------

.. toctree::
   :maxdepth: 1
   
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

Description
-----------

A profile is a recorded collection of fields relating to a specific MPI library.

+-------------+--------------------------------------------------------------+
| Field       | Description                                                  |
+=============+==============================================================+
| `name`      | A name by which the profile is accessed and invoked          |
+-------------+--------------------------------------------------------------+
| `image`     | The path of a container image                                |
+-------------+--------------------------------------------------------------+
| `backend`   | Identifier for a technology to launch the container with     |
+-------------+--------------------------------------------------------------+
| `source`    | Path of a script to source in the container before execution |
+-------------+--------------------------------------------------------------+
| `files`     | List of files to make accessible to the running program      |
+-------------+--------------------------------------------------------------+
| `libraries` | List of libraries to overload in the running program         |
+-------------+--------------------------------------------------------------+

**e4s-cl** stores profiles to simplify :ref:`launch commands<launch>`.
Profiles are accessed and edited using the `profile` sub-commands.

Profile Selection
-----------------

A profile can be selected using the :ref:`profile select<profile_select>` command. The target profile is then implicitly used for most of the commands taking a profile as an argument.

A unique profile can be selected at a time. Switching selection is done by selecting another profile. A selection can also be canceled by using :ref:`profile unselect<profile_unselect>`.
