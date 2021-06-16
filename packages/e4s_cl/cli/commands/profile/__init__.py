"""
Profiles are a key component of **e4s-cl**. They are used to greatly \
        reduce the amount of information to input on a command line by \
        recording chosen arguments.

Instead of listing all necessary files and libraries to use for every command, \
        passing a profile containing those files as an argument vastly \
        improves readability.

Profiles are accessed and edited using the `profile` sub-commands.

Contents
--------

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

Profile Creation
----------------

Profiles can be created with the :ref:`init<init>`, \
        :ref:`profile detect<profile_detect>` and \
        :ref:`profile create<profile_create>` commands.

The commands :ref:`init<init>` and :ref:`profile detect<profile_detect>` will \
        create a profile dynamically according to the execution of a \
        reference MPI program.

The :ref:`profile create<profile_create>` command will create an empty profile \
        to complete at the user's discretion.

.. caution::

    MPI libraries often dynamically use files and libraries without warning, \
            and the absence of those unlisted files during execution more \
            often than not results in a crash or segmentation fault. Please \
            ensure you acknowledge the result of \
            :ref:`profile detect<profile_detect>` when creating an empty profile.

Profile Selection
-----------------

A profile can be selected using the :ref:`profile select<profile_select>` \
        command. The target profile is then implicitly used for most of the \
        commands taking a profile as an argument.

A unique profile can be selected at a time. Switching selection is done by \
        selecting another profile. A selection can also be canceled by using \
        :ref:`profile unselect<profile_unselect>`.
"""

from e4s_cl.cli.cli_view import RootCommand
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.detect import COMMAND as detect_command


def _profile_fields():
    for name, data in Profile.__attributes__().items():
        yield " - %(name)s: %(description)s" % {
            'name': name.capitalize(),
            'description': data['description'].capitalize()
        }


HELP_PAGE = """The profile command is used to access and manage profiles.

e4s-cl uses profiles to keep track of execution parameters. These parameters
can then be omitted from the command line given the corresponding profile.

Profiles have the following fields:
%(detail)s

It is highly encouraged to use e4s-cl facilities to create profiles.
The %(detect)s command will complete the selected profile
from the execution of the command passed as an argument. This is the most
secure way to get a accurate profile.

The e4s-cl init command will create a new profile from the available
MPI library, using generic arguments. Those arguments may not correspond to
real use-cases and may result in an incomplete profile.""" % {
    'detect': detect_command.command,
    'detail': "\n".join(_profile_fields())
}

COMMAND = RootCommand(Profile,
                      __name__,
                      group="configuration",
                      help_page_fmt=HELP_PAGE)
