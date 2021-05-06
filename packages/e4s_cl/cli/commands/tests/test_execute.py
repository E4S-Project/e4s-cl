from e4s_cl import tests
from e4s_cl.cf.libraries import host_libraries
from e4s_cl.cli.commands.__execute import COMMAND


class ExecuteTest(tests.TestCase):
    def test_nonexistent(self):
        argv = ['--backend', 'neverImplemented', '--image', '/dev/null', 'ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)
        argv = ['--backend', 'bash', '--image', '/this/does/not/exist', 'ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)

    """
    Tests that broke when the script import was implemented.
    Finding a portable mock container technology would be able to get them
    working again.
    def test_simple(self):
        argv = ['--backend', 'bash', '--image', '/dev/null', 'ls']
        stdout, stderr = self.assertCommandReturnValue(0, COMMAND, argv)

    def test_libraries(self):
        libraries = []
        for soname in filter(lambda x: 'libc.so' in x,
                             host_libraries().keys()):
            libraries.append(host_libraries()[soname])
        argv = ['--backend', 'bash', '--image', '/dev/null', '--libraries'
                ] + libraries + ['ls']
        self.assertCommandReturnValue(0, COMMAND, argv)

        argv = ['--backend', 'bash', '--image', '/dev/null', '--libraries'
                ] + ['/tmp' + lib for lib in libraries] + ['ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)

    def test_files(self):
        files = [
            '/etc/fstab', '/etc/group', '/etc/hosts', '/etc/hostname',
            '/etc/localtime', '/etc/passwd'
        ]

        argv = ['--backend', 'bash', '--image', '/dev/null', '--files'
                ] + files + ['ls']
        self.assertCommandReturnValue(0, COMMAND, argv)

        argv = ['--backend', 'bash', '--image', '/dev/null', '--files'
                ] + ['/tmp' + f for f in files] + ['ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)
    """
