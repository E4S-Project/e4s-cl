from e4s_cl.util import which
from e4s_cl.cf.containers import Container

class SingularityContainer(Container):
    def run(self, command):
        params = {
                "bin": which('singularity'),
                "image": self.image,
                "files": self.format_bound(),
                "command": command
                }
        container_cmd = "{bin} exec {image} {files} {command}".format(**params)
        print(container_cmd)

    def format_bound(self):
        files = ','.join(self.bound)
        if files:
            return "-B {0}".format(files)
        return ""

    @staticmethod
    def is_available():
        return which('singularity') != None

MIMES = ['simg']
AVAILABLE = SingularityContainer.is_available()
CLASS = SingularityContainer
