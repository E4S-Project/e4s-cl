=================
How it works
=================

**e4s-cl** uses file binding and environment manipulation to allow accessing host libraries from inside of the container. The following outlines how this is done.

MPI translation
````````````````

The MPI standard abstracts a great deal of work from the developer to make
development as simple as possible. MPI libraries have to do a lot behind the
scenes, and different approaches are the reason so many library implementations
exist.

This means switching between libraries is not a plug-and-play experience.
The standard is loose enough for the binary interfaces to differ slightly, and
even if they match, the dependencies might differ and prevent operation.

**e4s-cl** simplifies this by tracking MPI library vendor, version and dependencies to facilitate this switch. A binary compiled with one library can then be used with another, to allow making full use of individual libraries.

When libraries are compatible at the binary level, they are swapped seamlessly using the dynamic linker. If not, `Wi4MPI <https://github.com/cea-hpc/wi4mpi>`_ is used to translate MPI calls between implementations.

Launch procedure
`````````````````

.. figure:: https://raw.githubusercontent.com/E4S-Project/e4s-cl/master/assets/images/e4scl_structure.svg
   :alt: container launcher elements diagram

   Diagram of execution using an MPI launcher

**e4s-cl** will first parse the command line and identify the launcher from
the final command. This is done by using a list of known launcher and options,
and can fail; use dashed (:kbd:`--`) to explicitly split the two.

The identified launcher is then used to spawn worker processes. Those
processes take over the original command given on the command line, and
prepare the environment before running this same command in a container.

If no launcher is given, the process is just created on the same host.

This preparation consists of multiple steps:

- The requested library list is resolved, completed if needed, then checked for
  compatibility. Files in the processed list are then bound to the container 
  in a special directory (:code:`/.e4s-cl/hostlibs`) to be made accessible by
  the linker through the environment.

- The requested files are bound in-place, meaning they will appear to the
  contained process as they do on the host. This depends on the backend as some
  container technologies do not allow files to be bound.

- A script is prepared to run the given command after the potential source
  script, then bound to the container in the :code:`/.e4s-cl` directory.
