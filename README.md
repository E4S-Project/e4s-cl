# E4S Container Launcher

E4S container launcher is a tool to ease running MPI applications in E4S containers with host libraries. Built upon the [MPICH ABI Compatibility Initiative](https://www.mpich.org/abi/).

## Running an application

Running an application with E4S Container Launcher can be as simple as prefixing the launcher command by `e4s-cl launch`.

```
e4s-cl launch mpirun -np 4 ./foo
```

However, some configuration is required to get to that point.

### Command line options

The `launch` directive accepts the basic options for running a program, being the type of image to use, and the libraries and files to import from the host.

|Option|Accepted argument|Optionnal|
|-|-|-|
|`--backend`|container technology to use: `singularity/docker/etc`|No|
|`--image`|path to imagefile|No|
|`--libraries`|list of library paths|Yes|
|`--files`|list of file paths|Yes|

Libraries are different than files in the sense that once imported, they will be made accessible on the guest container, but in a special location. Files on the other hand will be left as-is in the filesystem tree.

```
e4s-cl launch --backend singularity --image ecp.smig --libraries /opt/mpich/lib/libmpi.so mpirun -np 4 ./foo
```

This approach is discouraged, but powerful enough if you know what your library relies on. Using profiles is a safer path.

### Profiles

Profiles simplify the invocation of the `launch` directive by recording the libraries to use, along with the container image and backend.
Most of the arguments are then implicitly passed by selecting a profile (using `e4s profile select`).

```
e4s-cl profile select mvapich2/2.3.2
e4s-cl launch srun -n 2 --mpi=pmi2 ./foo
```

## Installation

```
git clone https://github.com/spoutn1k/e4s-cl
cd e4s-cl
make install
export PATH=$HOME/e4s-cl-0.0.0/bin:$PATH

make completion # Optionnal, only on bash shells
```

## Creating profiles

### Using `profile detect`

A built-in tool can create profile templates for you. To use it, simply compile a program with the MPI library of your choice, then analyse it using `e4s-cl profile detect <LAUNCHER> <LAUNCHER OPTIONS> <EXECUTABLE>`.
The process is then analyzed to get a complete list of all the libraries it used during its execution.
This list may be too complete however, and some libraries need to be removed in order to run correctly.
By using `ptrace`, this method ensures all necessary libraries are listed, even if they are opened at run-time.

### Manually

If you know what a library relies on when running, you can manually maintain profiles using `e4s-cl profile create` and `e4s-cl profile edit`. You do not need to list all the dynamic dependencies to import however, as the linker is called on every work node prior to execution to ensure the validity of the dynamic dependencies. Be warned that some libraries fail without having access to special files on the filesystem. Those files might be dynamic libraries imported by path instead of using the linker, and those need to be imported as files to ensure their location is not modified.

## How it works

`e4s-cl` wraps around launchers to execute a small amount of pre-processing before launching a container.
It recursively calls itself with the launcher used by the user before executing the command, analyses the library environment from the host, and uses on the container technology to bind the necessary files and libraries in the guest container.

![structure](https://github.com/spoutn1k/e4s-cl/raw/master/assets/images/e4scl_structure.png)
