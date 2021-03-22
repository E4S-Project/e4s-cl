# E4S Container Launcher

E4S container launcher is a tool to ease running MPI applications in E4S containers with host libraries. Built upon the [MPICH ABI Compatibility Initiative](https://www.mpich.org/abi/).

__Check out the documentation [here](https://e4s-project.github.io/e4s-cl/) !__. 

## Usage

Running an application with E4S Container Launcher can be as simple as prefixing the launcher command by `e4s-cl launch`.

```
e4s-cl init
e4s-cl launch mpirun -np 4 ./foo
```

The full details on execution and configuration can be found [here](https://e4s-project.github.io/e4s-cl/quickstart.html).

## Installation

Install using the provided `Makefile`. The installation location can be set using the `INSTALLDIR` variable:

```
git clone https://github.com/E4S-Project/e4s-cl
cd e4s-cl
make INSTALLDIR=<prefix> install
```

Once the installation succeeds, add `<prefix>/bin` to your `PATH`.

The full details on installation targets can be found [here](https://e4s-project.github.io/e4s-cl/installation.html).

## How it works

`e4s-cl` wraps around launchers to execute a small amount of pre-processing before launching a container.
It recursively calls itself with the launcher used by the user before executing the command, analyses the library environment from the host, and uses on the container technology to bind the necessary files and libraries in the guest container.

![structure](https://github.com/E4S-Project/e4s-cl/raw/master/assets/images/e4scl_structure.png)
