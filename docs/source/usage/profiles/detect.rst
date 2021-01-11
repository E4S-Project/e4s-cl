**detect** - Create a profile from a MPI library
================================================

**e4s-cl profile detect** < NAME > < MPI launcher command >

The **profile detect** command will create a profile from the analysis of a MPI command.
This process uses system call interception to produce an exhaustive list of files required by the MPI process.
A few point must be respected:

* The MPI launcher and binary shall use the host's MPI library, to be imported in the future containers;
* The MPI program shall call at least one (1) collective to ensure the network stack is used;
* The process shall be run on multiple nodes using the target network. Failure to do so may result in erroneous detection of communication libraries and thus may create communication errors when using the profile.
