.. _profile:

`profile` - Edit and manage profiles
=====================================

A profile is a recorded collection of fields relating to a specific MPI library.
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
