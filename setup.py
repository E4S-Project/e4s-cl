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

import os
import setuptools
from setuptools.command.install import install

setuptools.setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    keywords=KEYWORDS,
    classifiers=CLASSIFIERS,
    packages=setuptools.find_packages("packages"),
    package_dir={"": "packages"},
    install_requires=['termcolor', 'texttable'],
)
