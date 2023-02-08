# E4S Container Launcher

E4S container launcher is a tool to simplify running MPI applications in E4S containers with host libraries. This project is built upon the [MPICH ABI Compatibility Initiative](https://www.mpich.org/abi/) and CEA's [Wi4MPI](https://github.com/cea-hpc/wi4mpi).

__Check out the documentation [here](https://e4s-cl.readthedocs.io/en/latest/index.html) !__

## Usage

Running an application with E4S Container Launcher can be as simple as prefixing the launcher command by `e4s-cl launch`.

```
e4s-cl init
e4s-cl launch mpirun -np 4 ./foo
```

The full details on execution and configuration can be found [here](https://e4s-cl.readthedocs.io/en/latest/quickstart.html).

## How it works

### Creating containers

`e4s-cl` wraps around standard MPI-capable launchers to execute a small amount of pre-processing before creating containers in which to run commands.
This processing includes analyzing the library environment from the host, to bind select libraries to the container in order to make them accessible to the running process.

![structure](https://github.com/E4S-Project/e4s-cl/raw/master/assets/images/e4scl_structure.png)

### The concept of profile

One of the core components of the tool are profiles. They contain specific information about an execution environment that can be reproduced, such as container image and technology, or files and libraries to import in the containers.

They can be accessed and modified using the `e4s-cl profile` commands.
```
[jskutnik@spoutnik ~]$ e4s-cl profile list
============= Profile Configurations (/home/jskutnik/.local/e4s_cl/user.json) ==
+----------+------------+-------------+------------+-----------+-------+--------+
| Selected |    Name    |   Backend   |   Image    | Libraries | Files | WI4MPI |
+==========+============+=============+============+===========+=======+========+
|          |  MPICH_3.4 | singularity |       None |    16     |   1   |   No   |
+----------+------------+-------------+------------+-----------+-------+--------+
```

Profiles are also used as intermediate outputs of the program. `e4s-cl profile detect` will analyze a given binary to list all its library and file dependencies. Those results are stored into a given profile to be reused.

## Installation

`e4s-cl` requires `python3.7+` to run. If you do not have access to a compatible version, the guided installation process will download a conda interpreter to run the project.

### Guided standalone installation

You can install `e4s-cl` and a dedicated `python` interpreter using the provided `Makefile`. The installation location can be set using the `INSTALLDIR` variable:

```
git clone https://github.com/E4S-Project/e4s-cl
cd e4s-cl
make INSTALLDIR=<prefix> install
```

Once the installation succeeds, add `<prefix>/bin` to your `PATH`.

### `python` package installation

If you would rather install `e4s-cl` using standard `python` packaging facilities, you may install using `pip`:

```
git clone https://github.com/E4S-Project/e4s-cl
cd e4s-cl
pip install .
```

The full details on installation targets can be found [here](https://e4s-cl.readthedocs.io/en/latest/installation.html).
