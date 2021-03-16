.. _profile_detect:

**detect** - Create a profile from a MPI library
================================================

Usage
--------

**e4s-cl profile detect** [ `OPTIONS` ] < MPI launcher command >

OPTIONS := { **-p**\[rofile] }

Description
------------

The **profile detect** command will create a profile from the analysis of a MPI binary's execution.
This process uses system call interception to produce an exhaustive list of files required by the MPI process.

.. warning::
    To get a complete dependency detection, it is best to follow those guidelines:

    * The MPI launcher and binary should use the host's MPI library, to be imported in the future containers;
    * The MPI program should call at least one collective to ensure the use of the network stack;
    * The process should be run on multiple nodes using the target network. Failure to do so may result in erroneous detection of communication libraries and thus may create communication errors when using the profile.

Use **-p**/**--profile** to select a output profile. If the option is not present, the selected profile will be overwritten instead.

.. warning::
   Not specifying a profile will overwrite the selected profile on success !
