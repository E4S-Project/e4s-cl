#!/usr/bin/env python3

import os, sys, setuptools, subprocess
from setuptools.command.install import install as InstallCommand

PACKAGE_TOPDIR = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(PACKAGE_TOPDIR, 'packages'))

METADATA_MODULE = """\"\"\"File generated during install\"\"\"
__version__ = '%(version)s'
__commit__ = '%(commit)s'
"""


def _version():
    version_file = os.path.join(PACKAGE_TOPDIR, "VERSION")
    commit_file = os.path.join(PACKAGE_TOPDIR, "COMMIT")

    if os.path.exists(version_file):
        with open(version_file) as fin:
            version = fin.readline()
    else:
        try:
            version = subprocess.check_output(['./scripts/version.sh'])
        except (FileNotFoundError, subprocess.CalledProcessError):
            version = "0.0.0"

    if os.path.exists(commit_file):
        with open(commit_file) as fin:
            commit = fin.readline()
    else:
        commit = "Unknown"

    metadata_destination = os.path.join(PACKAGE_TOPDIR, 'packages', 'e4s_cl',
                                        'version.py')

    with open(metadata_destination, 'w') as embedded_version_file:
        embedded_version_file.write(
            METADATA_MODULE % {
                'version': version.strip(),
                'commit': commit.strip(),
            })

    return version.strip()


NAME = "e4s-cl"

VERSION = _version()

# Package author information
AUTHOR = "Jean-Baptiste Skutnik"
AUTHOR_EMAIL = "jskutnik@uoregon.edu"

# Package short description
DESCRIPTION = "A command-line utility to run MPI projects in E4S containers"

# Package long description
LONG_DESCRIPTION = \
"""
This program acts as a launcher to try and use MPICH-compatible binaries in 
containers while using the libraries available on the host environment.
Binaries are analysed to bind their dynamic dependencies.
"""

# Package software license
LICENSE = "MIT"

# Package keywords
KEYWORDS = ["E4S", "container", "MPI"]

# Package homepage
HOMEPAGE = "http://github.com/E4S-Project"

# PyPI classifiers
CLASSIFIERS = [
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',

    # Pick your license as you wish (should match "license" above)
    'License :: MIT License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.9',
]


class Install(InstallCommand):
    """Customize the install command with new lib, script, and data installation locations."""
    def initialize_options(self):
        InstallCommand.initialize_options(self)

    def finalize_options(self):
        # Distuilts defines attributes in the initialize_options() method
        # pylint: disable=attribute-defined-outside-init
        InstallCommand.finalize_options(self)
        self.install_scripts = os.path.join(self.prefix, 'bin')
        self.install_lib = os.path.join(self.prefix, 'packages')
        self.install_data = os.path.join(self.prefix)
        self.record = os.path.join(self.prefix, 'install.log')
        self.optimize = 1

    def run(self):
        InstallCommand.run(self)


setuptools.setup(name=NAME,
                 version=_version(),
                 author=AUTHOR,
                 author_email=AUTHOR_EMAIL,
                 description=DESCRIPTION,
                 license=LICENSE,
                 keywords=KEYWORDS,
                 classifiers=CLASSIFIERS,
                 scripts=['scripts/e4s-cl'],
                 packages=setuptools.find_packages("packages"),
                 package_dir={"": "packages"},
                 cmdclass={'install': Install})
