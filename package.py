# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import *


class PyE4sCl(PythonPackage):
    """Container Launcher for E4S containers, facilitating MPI library
    translations"""

    maintainers = ["spoutn1k", "FrederickDeny"]
    homepage = "https://e4s-cl.readthedocs.io"
    url = "TBD"
    git = "https://github.com/E4S-Project/e4s-cl"

    tags = ["e4s"]

    version("1.0.0", sha256="TBD")

    depends_on("python@3.7:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
