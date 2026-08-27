from os import environ, pathsep
from pathlib import Path
from unittest.mock import patch

import tests
from e4s_cl.cf.containers import Container


class SifLikeContainerTestMixin:

    BACKEND_NAME = None
    ENV_PREFIX = None
    CONFIG_EXECUTABLE = None
    TEST_CONFIGURATION = None
    DEFAULT_CONFIGURATION = None

    def _container(self):
        return Container(name=self.BACKEND_NAME)

    def test_additional_options_config(self):
        from e4s_cl import config

        container = self._container()
        command = ['']

        runtime_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, runtime_command)

        config.update_configuration(self.TEST_CONFIGURATION)
        runtime_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], runtime_command)

        config.update_configuration(self.DEFAULT_CONFIGURATION)
        runtime_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, runtime_command)

    def test_additional_options_environment(self):
        container = self._container()
        command = ['']

        runtime_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, runtime_command)

        environ[f'E4S_CL_{self.ENV_PREFIX}_OPTIONS'] = "--nocolor -s"
        environ[f'E4S_CL_{self.ENV_PREFIX}_EXEC_OPTIONS'] = "--hostname XxmycoolcontainerxX"
        runtime_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], runtime_command)

        del environ[f'E4S_CL_{self.ENV_PREFIX}_OPTIONS']
        del environ[f'E4S_CL_{self.ENV_PREFIX}_EXEC_OPTIONS']
        runtime_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, runtime_command)

    def test_executable(self):
        """Assert the default executable comes from $PATH"""
        container = self._container()

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"

        self.assertEqual(tests.ASSETS / 'bin' / self.BACKEND_NAME,
                         container._executable())

        environ['PATH'] = default_path

    def test_executable_config(self):
        """Assert the executable is read from the configuration"""
        from e4s_cl import config

        container = self._container()

        config.update_configuration(self.TEST_CONFIGURATION)
        self.assertEqual(self.CONFIG_EXECUTABLE, container._executable())

        config.update_configuration(self.DEFAULT_CONFIGURATION)

    def test_executable_env(self):
        """Assert the executable is read from the environment"""
        container = self._container()

        env_var = f'E4S_CL_{self.ENV_PREFIX}_EXECUTABLE'
        environ[env_var] = str(tests.ASSETS / 'bin' / f'{self.BACKEND_NAME}-env')
        self.assertEqual(tests.ASSETS / 'bin' / f'{self.BACKEND_NAME}-env',
                         container._executable())

        del environ[env_var]

    def test_executable_priority(self):
        """Assert environment has precedence over config and config over default"""
        from e4s_cl import config

        container = self._container()

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"
        config.update_configuration(self.TEST_CONFIGURATION)

        env_var = f'E4S_CL_{self.ENV_PREFIX}_EXECUTABLE'
        environ[env_var] = str(tests.ASSETS / 'bin' / f'{self.BACKEND_NAME}-env')
        self.assertEqual(tests.ASSETS / 'bin' / f'{self.BACKEND_NAME}-env',
                         container._executable())

        del environ[env_var]
        self.assertEqual(self.CONFIG_EXECUTABLE, container._executable())

        config.update_configuration(self.DEFAULT_CONFIGURATION)
        self.assertEqual(tests.ASSETS / 'bin' / self.BACKEND_NAME,
                         container._executable())

        environ['PATH'] = default_path

    def test_gpu_runtime_flag_nvidia_only(self):
        container = self._container()

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libnvidia-ml.so.1']):
            runtime_command = container._prepare([''])

        self.assertIn('--nv', runtime_command)
        self.assertNotIn('--rocm', runtime_command)

    def test_gpu_runtime_flag_rocm_only(self):
        container = self._container()

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libamdhip64.so.6', 'libhsa-runtime64.so.1']):
            runtime_command = container._prepare([''])

        self.assertIn('--rocm', runtime_command)
        self.assertNotIn('--nv', runtime_command)

    def test_gpu_runtime_flag_ambiguous_dual_stack(self):
        container = self._container()

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libnvidia-ml.so.1', 'libamdhip64.so.6']):
            runtime_command = container._prepare([''])

        self.assertIn('--nv', runtime_command)
        self.assertNotIn('--rocm', runtime_command)

    def test_gpu_runtime_flag_dual_stack_prefers_nvidia_workload_hint(self):
        container = self._container()
        container.add_ld_preload('/usr/lib64/libcuda.so.1')

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libnvidia-ml.so.1', 'libamdhip64.so.6']):
            runtime_command = container._prepare([''])

        self.assertIn('--nv', runtime_command)
        self.assertNotIn('--rocm', runtime_command)

    def test_gpu_runtime_flag_dual_stack_prefers_rocm_workload_hint(self):
        container = self._container()
        container.add_ld_preload('/opt/rocm/lib/libamdhip64.so.6')

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libnvidia-ml.so.1', 'libamdhip64.so.6']):
            runtime_command = container._prepare([''])

        self.assertIn('--rocm', runtime_command)
        self.assertNotIn('--nv', runtime_command)

    def test_gpu_runtime_flag_dual_stack_prefers_rocm_command_hint(self):
        container = self._container()

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libnvidia-ml.so.1', 'libamdhip64.so.6']):
            runtime_command = container._prepare([Path('rocminfo')])

        self.assertIn('--rocm', runtime_command)
        self.assertNotIn('--nv', runtime_command)

    def test_gpu_runtime_flag_prefers_resolved_rocm_libraries(self):
        container = self._container()
        container.gpu_runtime_libraries = [
            '/opt/rocm-7.1.1/lib/libamdhip64.so.7',
            '/opt/rocm-7.1.1/lib/librccl.so.1',
            '/packages/mvapich2/plus/4.1-rocm7.1.1/lib/ucx/libuct_rocm.so.0',
        ]

        with patch('e4s_cl.cf.containers.sif_like.cache_libraries',
                   return_value=['libnvidia-ml.so.1', 'libamdhip64.so.6']):
            runtime_command = container._prepare([''])

        self.assertIn('--rocm', runtime_command)
        self.assertNotIn('--nv', runtime_command)
