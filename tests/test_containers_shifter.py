from os import getenv, getcwd, environ, pathsep
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import skipIf
from pathlib import Path
import tests
from e4s_cl import config
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
)
from e4s_cl.cf.containers.shifter import _parse_config

SAMPLE_CONFIG = """#system (required)
#
# Name of your system, e.g., edison or cori. This name must match a configured 
# system in the imagegw. This is primarily used by shifterimg to self-identify 
# which system it is representing.
#
system=perlmutter
siteFs=/path1:/path1;\\
    /path2:/path2;
siteEnv=SHIFTER_RUNTIME=1
module_test_siteFs = test
this line is an issue and should be dropped
"""

EXPECTED_CONFIG = dict(system='perlmutter',
                       siteFs='/path1:/path1;/path2:/path2;',
                       siteEnv='SHIFTER_RUNTIME=1',
                       module_test_siteFs='test')

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'shifter-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
shifter:
  executable: '{CONFIG_EXECUTABLE}'
  options: ['--workdir=/opt', '-V', '/opt:/opt:ro']
""")


class ContainerTestShifter(tests.TestCase):

    def test_parse_config(self):
        with NamedTemporaryFile('w', delete=False) as config:
            config.write(SAMPLE_CONFIG)
            config_file = config.name

        directives = _parse_config(config_file)

        self.assertSetEqual(set(EXPECTED_CONFIG.keys()),
                            set(directives.keys()))
        self.assertSetEqual(set(EXPECTED_CONFIG.values()),
                            set(directives.values()))

    def test_create(self):
        container = Container(name='shifter', image='test')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    def test_run_image(self):
        container = Container(name='shifter', image='imagenametest')
        command = ['']
        container_cmd = container._prepare(command)
        self.assertIn('imagenametest', ' '.join(map(str, container_cmd)))

    def test_run_mpirun(self):
        container = Container(name='shifter', image='dummyimagename')
        command = ['mpirun -n 2 ls']
        container_cmd = container._prepare(command)
        self.assertIn(command[0], ' '.join(map(str, container_cmd)))

    def test_bind_file(self):
        container = Container(name='shifter')

        target = Path('/tmp')
        dest = Path('/etc')
        contained_dest = Path("/etc/skel")
        option = FileOptions.READ_WRITE

        container.bind_file(target)
        self.assertIn(BoundFile(target, target, FileOptions.READ_ONLY),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=dest)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=dest)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest, option=option)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_WRITE),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=contained_dest)
        self.assertIn(BoundFile(target, contained_dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest, option=option)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_WRITE),
                      list(container.bound))

    def test_bind_relative(self):
        container = Container(name='shifter')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file = Path('/proc/meminfo')

        container.bind_file(target)
        files = set(map(lambda x: x.origin, container.bound))

        self.assertSetEqual({ref, file}, files)

    def test_prepare_import_container_dir(self):
        """
        Assert CONTAINER_DIR imports will trigger the creation of a mock directory
        """

        def contents(directory: Path):
            return set(map(lambda x: x.name, directory.iterdir()))

        container = Container(name='shifter')
        temp = TemporaryDirectory()
        path = Path(temp.name)

        container.bind_file(
            Path(__file__),
            Path(container.import_binary_dir) / Path(__file__).name)

        volumes = container._setup_import(path)

        self.assertIn(container.import_binary_dir.name, contents(path))
        self.assertIn(
            Path(__file__).name,
            contents(path / container.import_binary_dir.name))

        temp.cleanup()

    def test_prepare_import_etc_files(self):
        """
        Assert importing /etc files fails
        """

        def contents(directory: Path):
            return set(map(lambda x: x.name, directory.iterdir()))

        container = Container(name='shifter')
        temp = TemporaryDirectory()
        path = Path(temp.name)

        # Files to attempt binding, must ideally be present on every system
        files = ['/etc/ld.so.cache', '/etc/ld.so.conf.d/']

        for file in files:
            container.bind_file(file, file)

        volumes = container._setup_import(path)

        for bind in volumes:
            for file in files:
                self.assertNotIn(file, volumes)

        temp.cleanup()

    def test_additional_options_config(self):
        container = Container(name='shifter')
        command = ['']

        shifter_command = container._prepare(command)
        for option in {'--workdir=/opt', '-V', '/opt:/opt:ro'}:
            self.assertNotIn(option, shifter_command)

        config.update_configuration(TEST_CONFIGURATION)
        shifter_command = container._prepare(command)
        self.assertContainsInOrder([
            '--workdir=/opt',
            '-V',
            '/opt:/opt:ro',
        ], shifter_command)

        config.update_configuration(DEFAULT_CONFIGURATION)
        shifter_command = container._prepare(command)
        for option in {'--workdir=/opt', '-V', '/opt:/opt:ro'}:
            self.assertNotIn(option, shifter_command)

    def test_additional_options_environment(self):
        container = Container(name='shifter')
        command = ['']

        shifter_command = container._prepare(command)
        for option in {'--workdir=/opt', '-V', '/opt:/opt:ro'}:
            self.assertNotIn(option, shifter_command)

        environ['E4S_CL_SHIFTER_OPTIONS'] = "--workdir=/opt -V /opt:/opt:ro"
        shifter_command = container._prepare(command)
        self.assertContainsInOrder([
            '--workdir=/opt',
            '-V',
            '/opt:/opt:ro',
        ], shifter_command)

        del environ['E4S_CL_SHIFTER_OPTIONS']
        shifter_command = container._prepare(command)
        for option in {'--workdir=/opt', '-V', '/opt:/opt:ro'}:
            self.assertNotIn(option, shifter_command)

    def test_executable(self):
        """Assert the default shifter executable comes from $PATH"""
        container = Container(name='shifter')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"

        self.assertEqual(tests.ASSETS / 'bin' / 'shifter',
                         container._executable())

        environ['PATH'] = default_path

    def test_executable_config(self):
        """Assert the shifter executable is read from the configuration"""
        container = Container(name='shifter')

        config.update_configuration(TEST_CONFIGURATION)
        self.assertEqual(tests.ASSETS / 'bin' / 'shifter-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

    def test_executable_env(self):
        """Assert the shifter executable is read from the environment"""
        container = Container(name='shifter')

        environ['E4S_CL_SHIFTER_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                   'shifter-env')
        self.assertEqual(tests.ASSETS / 'bin' / 'shifter-env',
                         container._executable())

        del environ['E4S_CL_SHIFTER_EXECUTABLE']

    def test_executable_priority(self):
        """Assert the environment has precedence over config and config over default"""
        container = Container(name='shifter')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"
        config.update_configuration(TEST_CONFIGURATION)
        environ['E4S_CL_SHIFTER_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                   'shifter-env')

        self.assertEqual(tests.ASSETS / 'bin' / 'shifter-env',
                         container._executable())

        del environ['E4S_CL_SHIFTER_EXECUTABLE']

        self.assertEqual(tests.ASSETS / 'bin' / 'shifter-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

        self.assertEqual(tests.ASSETS / 'bin' / 'shifter',
                         container._executable())

        environ['PATH'] = default_path
