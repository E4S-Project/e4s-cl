from e4s_cl import logger
from e4s_cl.util import host_libraries, create_subprocess_exp
from e4s_cl.cf.containers import Container

LOGGER = logger.get_logger(__name__)

EXECUTABLES = ['singularity']
MIMES = ['simg', 'sif']


class SingularityContainer(Container):
    def run(self, command, redirect_stdout=False):
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update(
            {'SINGULARITYENV_LD_PRELOAD': ":".join(self.ld_preload)})
        self.env.update(
            {'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self.format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []
        container_cmd = [self.executable, 'exec'
                         ] + nvidia_flag + [self.image.as_posix()] + command
        _, output = create_subprocess_exp(container_cmd,
                                          env=self.env,
                                          redirect_stdout=redirect_stdout)
        return output

    def format_bound(self):
        file_list = ["{}:{}:{}".format(*request) for request in self.bound]
        files = ','.join(file_list)
        if files:
            self.env.update({"SINGULARITY_BIND": files})

    def bind_env_var(self, key, value):
        new_key = "SINGULARITYENV_{}".format(key)
        self.env.update({new_key: value})

    def _has_nvidia(self):
        if not 'nvidia' in " ".join(host_libraries().keys()):
            LOGGER.warning("Disabling Nvidia support: no libraries found")
            return False
        return True


CLASS = SingularityContainer
