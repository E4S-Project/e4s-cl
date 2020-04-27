from e4s_cl import logger
from e4s_cl.util import which, create_subprocess_exp
from e4s_cl.cf.containers import Container

LOGGER = logger.get_logger(__name__)

class SingularityContainer(Container):
    def run(self, command, redirect_stdout=False):
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update({'SINGULARITYENV_LD_PRELOAD': ":".join(self.ld_preload)})
        self.env.update({'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self.format_bound()
        container_cmd = [which('singularity'), 'exec', '--nv', self.image.as_posix()] + command
        _, output = create_subprocess_exp(container_cmd, env=self.env, redirect_stdout=redirect_stdout)
        return output

    def format_bound(self):
        file_list = ["{}:{}:{}".format(*request) for request in self.bound]
        files = ','.join(file_list)
        if files:
            self.env.update({"SINGULARITY_BIND": files})

    def bind_env_var(self, key, value):
        new_key = "SINGULARITYENV_{}".format(key)
        self.env.update({new_key: value})

    @staticmethod
    def is_available():
        return which('singularity') is not None

MIMES = ['simg']
AVAILABLE = SingularityContainer.is_available()
CLASS = SingularityContainer
