#!/usr/bin/env python3

import os, sys, setuptools, subprocess
import importlib.util

# Load metadata from the package's version module
spec = importlib.util.spec_from_file_location(
    'version', os.path.join('e4s_cl', 'version.py'))
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)

NAME = "e4s-cl"

VERSION = metadata.__version__

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

# Package keywords
KEYWORDS = ["E4S", "container", "MPI"]

# PyPI classifiers
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Operating System :: POSIX :: Linux',
    'Intended Audience :: Science/Research',
    'License :: MIT License',
    'Natural Language :: English',
    'Programming Language :: Python :: 3',
]

install_options = {
    "name": NAME,
    "version": VERSION,
    "url": metadata.WEBSITE,
    "author": AUTHOR,
    "author_email": AUTHOR_EMAIL,
    "description": DESCRIPTION,
    "long_description": LONG_DESCRIPTION,
    "license": metadata.LICENSE,
    "keywords": KEYWORDS,
    "classifiers": CLASSIFIERS,
    "scripts": ['scripts/e4s-cl'],
    "packages": ['e4s_cl']
}

setuptools.setup(**install_options)
