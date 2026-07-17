"""
Module introducing singularity support
"""

from e4s_cl.cf.containers.sif_like import SifLikeContainer

NAME = 'singularity'
MIMES = ['.simg', '.sif']

class SingularityContainer(SifLikeContainer):
    """
    Singularity backend implementation.
    """

    executable_name = 'singularity'
    bind_env_var_name = 'SINGULARITY_BIND'
    env_prefix = 'SINGULARITYENV'
    export_ld_library_path = False


CLASS = SingularityContainer
