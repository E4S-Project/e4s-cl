========================
Developer documentation
========================

The project source code is split between different logical sections:

.. code::

    .
    ├── cf                          # Common Framework. Contains "library" 
                                    # modules to handles the moving parts
                                    # required for e4s-cl operation.
    │   ├── compiler.py             # Compiler detection
    │   ├── containers              # Container backend modules
    │   │   ├── apptainer.py
    │   │   ├── docker.py
    │   │   ├── dummy.py
    │   │   ├── host.py
    │   │   ├── __init__.py
    │   │   ├── podman.py
    │   │   ├── shifter.py
    │   │   └── singularity.py
    │   ├── detect_mpi.py           # MPI library classification module
    │   ├── __init__.py
    │   ├── launchers               # Process manager support modules
    │   │   ├── aprun.py
    │   │   ├── __init__.py
    │   │   ├── jsrun.py
    │   │   ├── mpirun.py
    │   │   └── slurm.py
    │   ├── libraries.py            # System library management. Wrapper
                                    # around python-sotools
    │   ├── storage                 # Data storage (for profiles)
    │   │   ├── __init__.py
    │   │   ├── levels.py
    │   │   └── local_file.py
    │   ├── template.py             # Entry point script support
    │   ├── trace.py                # Process execution analyzer. Wrapper for
                                    # python-ptrace
    │   ├── version.py
    │   └── wi4mpi                  # Wi4MPI installer and management methods
    │       ├── __init__.py
    │       └── install.py
    ├── cli                         # CLI definitions and command implementation
    │   ├── arguments.py
    │   ├── cli_view.py
    │   ├── command.py              # Command object definition
    │   ├── commands                # Commands. Each subdirectory defines a
                                    # subcommand. Each file defines a method
                                    # that executes on command invokation
    │   │   ├── __execute.py        # Wraps a container around a command on 
                                    # worker nodes. '__' signifies private 
                                    # status
    │   │   ├── help.py
    │   │   ├── __init__.py
    │   │   ├── init.py             # Create a profile from analysis of the
                                    # available MPI libraries
    │   │   ├── launch.py           # Launch a job from a login node
    │   │   ├── __main__.py
    │   │   └── profile             # Profile management
    │   │       ├── copy.py
    │   │       ├── create.py
    │   │       ├── delete.py
    │   │       ├── detect.py
    │   │       ├── diff.py
    │   │       ├── dump.py
    │   │       ├── edit.py
    │   │       ├── __init__.py
    │   │       ├── list.py
    │   │       ├── select.py
    │   │       ├── show.py
    │   │       └── unselect.py
    │   └── __init__.py
    ├── config.py                   # Configuration management
    ├── error.py                    # Error handling
    ├── __init__.py
    ├── logger.py                   # Log handling
    ├── __main__.py
    ├── model                       # MVC model implementations
    │   ├── __init__.py
    │   └── profile.py
    ├── mvc                         # MVC architecture infrastructure
    │   ├── controller.py
    │   ├── __init__.py
    │   └── model.py
    ├── scripts                     # Script entrypoints, as defined in pyproject.toml
    │   ├── e4s_cl_mpi_tester.py    # MPI analyzer helper, python script
                                    # loading and calling MPI functions 
    │   └── __init__.py
    ├── util.py                     # Misc utilities
    ├── variables.py                # Status altering variables
    └── version.py                  # Auto generated at install time

There are three main categories of actions **e4s-cl** can take:

Initialization
^^^^^^^^^^^^^^

The user requests the creation of a profile for a specific MPI library. **e4s-cl** will run a sample program with this library and intercept system calls to list all opened files. The path taken in the source code is roughly:

    - :code:`cli/commands/__main__.py`: Entrypoint of CLI and dispatch to init
    - :code:`cli/commands/init.py`: Init command. Create profile, select MPI from the arguments, then run a program with it.
    - :code:`cf/launchers/*.py`: Used to build the launch command to run the program with multiple processes
    - :code:`cli/commands/profile/detect.py`: Edit profile with files/libraries from traced processes
    - :code:`cf/trace.py`: Trace and intercept syscall of each process

Profile management
^^^^^^^^^^^^^^^^^^

    - :code:`cli/commands/__main__.py`: Entrypoint of CLI and dispatch to subcommand
    - :code:`cli/commands/cli_view.py`: Basic object management
    - :code:`cli/commands/profile/*.py`: More specific definitions for profiles

Job launch
^^^^^^^^^^

Launching a job is the most in-depth operation of **e4s-cl**. There are multiple steps taken to run e4s-cl on each node before starting a container and running the final user command in it.

    - :code:`cli/commands/__main__.py`: Entrypoint of CLI and dispatch to init
    - :code:`cli/commands/launch.py`: Select profile, insert __execute command in user command, spawn subprocess
    - :code:`cf/launchers/*.py`: Parse the command given by the user
    - :code:`cli/commands/__execute.py`: On-node execution, start container for analysis, then run it again to run command
    - :code:`cf/libraries.py`: Library dependency tree analysis and completion. Makes sure the most up to date libc (host or container's) is used in the container.
    - :code:`cf/containers/*.py`: Drivers to run containers
    - :code:`cf/template.py`: Script building module to create an entrypoint once in the container, to preload any libraries that might be RPATHed.

