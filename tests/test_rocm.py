import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import tests
from e4s_cl.cf.rocm import (
    ROCM_ASSETS,
    ROCM_PRELOAD_DENYLIST,
    RocmAsset,
    RocmDiscovery,
    diagnostic_env,
    discover_rocm_assets,
    find_asset_dir,
)


def _library(path):
    """Build a minimal stand-in for a sotools Library, keyed on binary_path."""
    return SimpleNamespace(binary_path=str(path))


class RocmAssetDiscoveryTests(tests.TestCase):
    """find_asset_dir / discover_rocm_assets: layout-agnostic bitcode resolution."""

    def _make_layout(self, temp_dir, lib_rel, bitcode_rel, markers=('ockl.bc', 'hip.bc')):
        root = Path(temp_dir)
        bitcode_dir = root / bitcode_rel
        bitcode_dir.mkdir(parents=True)
        for marker in markers:
            (bitcode_dir / marker).write_text('x')

        lib_path = root / lib_rel
        lib_path.parent.mkdir(parents=True, exist_ok=True)
        lib_path.write_text('fake')

        return lib_path, bitcode_dir

    def test_resolves_rocm7_style_layout(self):
        # e.g. /opt/rocm-7.1.1/lib/libamdhip64.so.7 with bitcode at
        # /opt/rocm-7.1.1/lib/llvm/lib/clang/20/lib/amdgcn/bitcode
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_path, bitcode_dir = self._make_layout(
                temp_dir,
                'rocm-7.1.1/lib/libamdhip64.so.7',
                'rocm-7.1.1/lib/llvm/lib/clang/20/lib/amdgcn/bitcode',
            )
            found = find_asset_dir(lib_path, ROCM_ASSETS[0])
            self.assertEqual(found, bitcode_dir)

    def test_resolves_flat_layout(self):
        # e.g. /opt/rocm-5.x/lib/libamdhip64.so with bitcode directly at
        # /opt/rocm-5.x/amdgcn/bitcode
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_path, bitcode_dir = self._make_layout(
                temp_dir,
                'rocm-5.4.0/lib/libamdhip64.so',
                'rocm-5.4.0/amdgcn/bitcode',
            )
            found = find_asset_dir(lib_path, ROCM_ASSETS[0])
            self.assertEqual(found, bitcode_dir)

    def test_does_not_match_directory_without_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / 'rocm-7.1.1'
            (root / 'amdgcn' / 'bitcode').mkdir(parents=True)
            # No ockl.bc/hip.bc marker files created
            lib_path = root / 'lib' / 'libamdhip64.so'
            lib_path.parent.mkdir(parents=True)
            lib_path.write_text('fake')

            # Isolate from any real ROCm install/tooling on the host, which
            # would otherwise be found by the environment-based fallback
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('ROCM_PATH', None)
                os.environ.pop('HIP_DEVICE_LIB_PATH', None)
                os.environ.pop('HIP_PATH', None)
                with patch('e4s_cl.cf.rocm._hipconfig_rocm_path',
                           return_value=None):
                    found = find_asset_dir(lib_path, ROCM_ASSETS[0])

            self.assertIsNone(found)

    def test_falls_back_to_rocm_path_env_var(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / 'rocm-7.1.1'
            bitcode_dir = root / 'amdgcn' / 'bitcode'
            bitcode_dir.mkdir(parents=True)
            (bitcode_dir / 'ockl.bc').write_text('x')

            # Library path itself gives no clue (e.g. resolved from a
            # non-ROCm location); only ROCM_PATH points at the real root
            unrelated_lib = Path(temp_dir) / 'somewhere' / 'libamdhip64.so'
            unrelated_lib.parent.mkdir(parents=True)
            unrelated_lib.write_text('fake')

            with patch.dict(os.environ, {'ROCM_PATH': str(root)}, clear=False):
                with patch('e4s_cl.cf.rocm._hipconfig_rocm_path',
                           return_value=None):
                    found = find_asset_dir(unrelated_lib, ROCM_ASSETS[0])

            self.assertEqual(found, bitcode_dir)

    def test_discover_rocm_assets_not_detected_without_trigger_library(self):
        libraries = [_library('/usr/lib/libmpi.so.12')]
        discovery = discover_rocm_assets(libraries)

        self.assertFalse(discovery.detected)
        self.assertEqual(discovery.resolved, [])
        self.assertEqual(discovery.missing, [])

    def test_discover_rocm_assets_resolved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_path, bitcode_dir = self._make_layout(
                temp_dir,
                'rocm-7.1.1/lib/libamdhip64.so.7',
                'rocm-7.1.1/lib/llvm/lib/clang/20/lib/amdgcn/bitcode',
            )
            libraries = [_library(lib_path), _library('/usr/lib/libmpi.so.12')]
            discovery = discover_rocm_assets(libraries)

            self.assertTrue(discovery.detected)
            self.assertEqual(discovery.missing, [])
            self.assertEqual(len(discovery.resolved), 1)
            host_dir, env_var, container_subdir = discovery.resolved[0]
            self.assertEqual(host_dir, bitcode_dir)
            self.assertEqual(env_var, 'HIP_DEVICE_LIB_PATH')
            self.assertEqual(container_subdir, 'rocm/bitcode')

    def test_discover_rocm_assets_detected_but_missing(self):
        # Trigger library present, but no bitcode anywhere findable
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_path = Path(temp_dir) / 'lib' / 'libamdhip64.so'
            lib_path.parent.mkdir(parents=True)
            lib_path.write_text('fake')

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('ROCM_PATH', None)
                os.environ.pop('HIP_DEVICE_LIB_PATH', None)
                os.environ.pop('HIP_PATH', None)
                with patch('e4s_cl.cf.rocm._hipconfig_rocm_path',
                           return_value=None):
                    discovery = discover_rocm_assets([_library(lib_path)])

            self.assertTrue(discovery.detected)
            self.assertEqual(discovery.resolved, [])
            self.assertEqual(discovery.missing, ['bitcode'])

    def test_detection_triggers_on_any_registered_soname(self):
        # libhsa-runtime64.so alone (without libamdhip64.so) must also
        # trigger detection, per the registry's trigger_prefixes.
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_path, bitcode_dir = self._make_layout(
                temp_dir,
                'rocm-7.1.1/lib/libhsa-runtime64.so.1',
                'rocm-7.1.1/amdgcn/bitcode',
            )
            discovery = discover_rocm_assets([_library(lib_path)])
            self.assertTrue(discovery.detected)
            self.assertEqual(discovery.resolved[0][0], bitcode_dir)


class RocmDiagnosticEnvTests(tests.TestCase):
    """diagnostic_env: automatic AMD_LOG_LEVEL hints for ROCm-backed launches."""

    def test_no_env_when_not_detected(self):
        discovery = RocmDiscovery(detected=False, resolved=[], missing=[])
        self.assertEqual(diagnostic_env(discovery, verbose=False), {})

    def test_default_level_when_resolved_cleanly(self):
        discovery = RocmDiscovery(detected=True,
                                  resolved=[(Path('/x'), 'HIP_DEVICE_LIB_PATH',
                                            'rocm/bitcode')],
                                  missing=[])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMD_LOG_LEVEL', None)
            result = diagnostic_env(discovery, verbose=False)
        self.assertEqual(result, {'AMD_LOG_LEVEL': '1'})

    def test_verbose_level_when_asset_missing(self):
        discovery = RocmDiscovery(detected=True, resolved=[], missing=['bitcode'])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMD_LOG_LEVEL', None)
            result = diagnostic_env(discovery, verbose=False)
        self.assertEqual(result, {'AMD_LOG_LEVEL': '4'})

    def test_verbose_level_when_debug_requested(self):
        discovery = RocmDiscovery(detected=True,
                                  resolved=[(Path('/x'), 'HIP_DEVICE_LIB_PATH',
                                            'rocm/bitcode')],
                                  missing=[])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMD_LOG_LEVEL', None)
            result = diagnostic_env(discovery, verbose=True)
        self.assertEqual(result, {'AMD_LOG_LEVEL': '4'})

    def test_respects_user_set_host_env(self):
        discovery = RocmDiscovery(detected=True,
                                  resolved=[(Path('/x'), 'HIP_DEVICE_LIB_PATH',
                                            'rocm/bitcode')],
                                  missing=[])
        with patch.dict(os.environ, {'AMD_LOG_LEVEL': '2'}, clear=False):
            result = diagnostic_env(discovery, verbose=False)
        self.assertEqual(result, {})

    def test_respects_existing_extra_env(self):
        discovery = RocmDiscovery(detected=True,
                                  resolved=[(Path('/x'), 'HIP_DEVICE_LIB_PATH',
                                            'rocm/bitcode')],
                                  missing=[])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMD_LOG_LEVEL', None)
            result = diagnostic_env(discovery, verbose=False,
                                    existing_env={'AMD_LOG_LEVEL': '3'})
        self.assertEqual(result, {})


class RocmPreloadDenylistTests(tests.TestCase):

    def test_rocprofiler_register_denied(self):
        self.assertIn('librocprofiler-register.so', ROCM_PRELOAD_DENYLIST)
