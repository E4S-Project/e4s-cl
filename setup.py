#!/usr/bin/env python3

NAME = "e4s-cl"

VERSION = "0.0"

# Package author information
AUTHOR = "ParaTools, Inc."
AUTHOR_EMAIL = "info@paratools.com"

# Package short description
DESCRIPTION = "A command-line utility to run projects in E4S containers"

# Package long description
LONG_DESCRIPTION = \
"""TODO"""

# Package software license
LICENSE = "BSD"

# Package keywords
KEYWORDS = ["E4S", "container"]

# Package homepage
HOMEPAGE = "http://www.taucommander.com/"

# PyPI classifiers
CLASSIFIERS = [
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',
    'Topic :: Software Development :: User Interfaces',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: BSD License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
]

import os, sys, setuptools, subprocess
from setuptools.command.install import install as InstallCommand

PACKAGE_TOPDIR = os.path.realpath(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(PACKAGE_TOPDIR, 'packages'))

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

def _version():
    version_file = os.path.join(PACKAGE_TOPDIR, "VERSION")

    if os.path.exists(version_file):
        with open(version_file) as fin:
            version = fin.readline()
    else:
        try:
            version = subprocess.check_output(['./scripts/version.sh'])
        except (FileNotFoundError, subprocess.CalledProcessError):
            version = "0.0.0"

    return version.strip()

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
