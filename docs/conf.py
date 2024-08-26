# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# -- Project information -----------------------------------------------------

project = 'E4S Container Launcher'
copyright = '2024, Frederick Deny'
author = 'Frederick Deny'

# The full version, including alpha/beta/rc tags
version = release = '1.0.4'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosectionlabel',
    'sphinx_toolbox.collapse',
    'sphinxcontrib.sass',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["css/main.css"]

sass_src_dir = "styles"
sass_out_dir = "_static/css"
sass_targets = {"main.scss": "main.css"}

# -- HTML theme options ------------------------------------------------------

# Make fonts bigger for clarity
options = {
    "code-font-size": "1em",
    "admonition-title-font-size": "1em",
    "admonition-font-size": ".92em",
    "font-size--small--2": ".90em",
    "font-size--small--3": ".82em",
}

html_theme_options = {
    "navigation_with_keys": True,
    "light_css_variables": options,
    "dark_css_variables": options
}

# -- Options for man output --------------------------------------------------

man_pages = [('index', 'e4s-cl', 'E4S Container Launcher', '', 1)]

# -- Options for code color  -------------------------------------------------

pygments_style = "gruvbox-light"
pygments_dark_style = "gruvbox-dark"
