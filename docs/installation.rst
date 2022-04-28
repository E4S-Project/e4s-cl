Installation
================

From source
-------------

To install a version from the sources, first clone the repository or download a `release <https://github.com/E4S-Project/e4s-cl/releases>`_:

.. code-block:: bash

    $ git clone https://github.com/E4S-Project/e4s-cl

Default installation
********************

Install **e4s-cl** using :code:`make install`. The installation directory can be modified using the :code:`INSTALLDIR` variable:

.. code-block:: bash

    $ make INSTALLDIR=<prefix> install

Or:

.. code-block:: bash

    $ make INSTALLDIR=<prefix> all [E4SCL_TARGETSYSTEM=<machine_name>]

The **e4s-cl** program will be copied over to :code:`<prefix>/bin`. On success, a message will be printed with the full path to add to your :code:`PATH`.

A python interpreter will be downloaded to ensure a compatible Python 3 version is available.

.. admonition:: :code:`E4SCL_TARGETSYSTEM` parameter

    Some machines have specific e4s-cl profiles tailored for them that can be downloaded and later accessed as builtin profiles. Those need to be enabled at installation using the :code:`E4SCL_TARGETSYSTEM` environment variable. This parameter requires e4s-cl to already be installed or to use the "all" target. Refer to the :ref:`system compatibility<system_compat>` page for details.

Completion
************

Automatic completion for commands and profiles can be installed by running :code:`make completion`. Whichever :code:`INSTALLDIR` chosen, a BASH completion script will be installed in :code:`$HOME/.local/share/bash-completion/completions/`. Sourcing it will enable **e4s-cl** completion in the shell; if the :code:`bash-completion` package is installed, it will be enabled for every new shell.

The :code:`INSTALLDIR` used for the :code:`make install` must be specified to tie the completion to the installed package.

.. code-block:: bash

    $ make INSTALLDIR=<prefix> completion
    $ source $HOME/.local/share/bash-completion/completions/e4s-cl

Manual page
************

This website can also be installed in the :code:`man` format to be accessible on the CLI with :code:`make man`. This will create a man page in :code:`$HOME/.local/share/man/man1` and update the manual page database. This is the default user-level install directory, but you may have to add :code:`$HOME/.local/share/man` to the :code:`MANPATH` environment variable to access it depending on your system's configuration.

The :code:`INSTALLDIR` used for the :code:`make install` must be specified to tie the manual to the installed package.

.. code-block:: bash

    $ make INSTALLDIR=<prefix> man
    $ export MANPATH=$HOME/.local/share/man:$MANPATH
    $ man e4s-cl

Full installation
******************

All of the above steps can be done at once by using :code:`make all`.

.. code-block:: bash

    $ make INSTALLDIR=<prefix>
