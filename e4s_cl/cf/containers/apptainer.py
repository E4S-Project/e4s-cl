"""
Module introducing singularity support
"""

from e4s_cl.cf.containers.sif_like import SifLikeContainer

NAME = 'apptainer'
MIMES = ['.simg', '.sif']

class ApptainerContainer(SifLikeContainer):
    """
    Apptainer backend implementation.
    """

    executable_name = 'apptainer'
    bind_env_var_name = 'APPTAINER_BIND'
    env_prefix = 'APPTAINERENV'
    export_ld_library_path = True


CLASS = ApptainerContainer
