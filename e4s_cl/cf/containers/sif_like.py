"""
Shared implementation for singularity/apptainer style backends.
"""

import os
from pathlib import Path
from typing import List

from e4s_cl import logger
from e4s_cl.util import run_subprocess
from e4s_cl.cf.libraries import cache_libraries
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError

LOGGER = logger.get_logger(__name__)

# Internal shared module (not a user-selectable backend)
NAME = '_sif_like'
CLASS = None
DEBUG_BACKEND = True

OPTION_STRINGS = {FileOptions.READ_ONLY: 'ro', FileOptions.READ_WRITE: 'rw'}

NVIDIA_LIBRARY_MARKERS = (
    'nvidia',
    'cuda',
    'cudart',
    'nccl',
    'gdrapi',
    'uct_cuda',
    'ucm_cuda',
)

ROCM_LIBRARY_MARKERS = (
    'rocm',
    'amdgpu',
    'amdgcn',
    'amdhip',
    'amd_comgr',
    'hsa',
    'hiprtc',
    'hip',
    'oclc',
    'ocml',
    'ockl',
    'rocblas',
    'rocsolver',
    'rocrand',
    'rocfft',
    'rocprofiler',
    'rocm_smi',
    'rccl',
    'uct_rocm',
    'ucm_rocm',
    'miopen',
)


class SifLikeContainer(Container):
    """Common behavior for singularity-like runtimes."""

    bind_env_var_name = ''
    env_prefix = ''
    export_ld_library_path = False

    def _working_dir(self):
        return ['--pwd', os.getcwd()]

    def __setup__(self):
        """
        Bind minimal directories stripped from the use of `--contain`
        """
        self.bind_file(Path.home(), option=FileOptions.READ_WRITE)

    def _format_bound(self):
        """Format bound files for singularity/apptainer bind env variable."""

        def _format():
            for file in self.bound:
                yield f"{file.origin}:{file.destination}:{OPTION_STRINGS[file.option]}"

        self.env.update({self.bind_env_var_name: ','.join(_format())})

    def _prepare(self, command: List[str], overload: bool = True) -> List[str]:
        """Return the command to run in a list of strings."""
        # As of mid-2022, apptainer still uses the `.singularity.d` folder.
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update({
            f"{self.env_prefix}_LD_PRELOAD": ":".join(self.ld_preload),
        })

        if self.export_ld_library_path:
            self.env.update({
                f"{self.env_prefix}_LD_LIBRARY_PATH": ":".join(self.ld_lib_path),
            })

        self._format_bound()
        gpu_runtime_flag = self._gpu_runtime_flag(command)

        return [
            *self._additional_options(),
            'exec',
            *self._working_dir(),
            *gpu_runtime_flag,
            *self._additional_options('exec'),
            self.image,
            *command,
        ]

    def bind_env_var(self, key, value):
        self.env.update({f"{self.env_prefix}_{key}": value})

    def _cache_libraries_string(self) -> str:
        return " ".join(cache_libraries()).lower()

    def _contains_any(self, text: str, markers) -> bool:
        return any(marker in text for marker in markers)

    def _workload_library_string(self) -> str:
        # gpu_runtime_libraries is populated by execute.py with the libraries
        # actually resolved/imported for this run (see Container.__init__).
        return " ".join([
            *self.ld_preload, *self.ld_lib_path,
            *getattr(self, 'gpu_runtime_libraries', [])
        ]).lower()

    def _bound_files_string(self) -> str:
        bound_paths = []
        for file in self.bound:
            bound_paths.extend((str(file.origin), str(file.destination)))
        return " ".join(bound_paths).lower()

    def _env_string(self) -> str:
        env_parts = []
        for key, value in self.env.items():
            env_parts.append(str(key))
            env_parts.append(str(value))
        return " ".join(env_parts).lower()

    def _marker_hits(self, text: str, markers) -> int:
        return sum(1 for marker in markers if marker in text)

    def _vendor_score(self, markers, workload_text: str, bound_text: str,
                      command_text: str, env_text: str) -> int:
        # Weight direct workload linkage strongest, then binds, then command/env.
        return (
            (5 * self._marker_hits(workload_text, markers)) +
            (3 * self._marker_hits(bound_text, markers)) +
            (2 * self._marker_hits(command_text, markers)) +
            (1 * self._marker_hits(env_text, markers))
        )

    def _gpu_runtime_flag(self, command: List[str]) -> List[str]:
        cache_text = self._cache_libraries_string()
        has_nvidia = self._has_nvidia(cache_text)
        has_rocm = self._has_rocm(cache_text)

        if not has_nvidia and not has_rocm:
            LOGGER.debug(
                "%s backend GPU auto-detection: disabled (no Nvidia/ROCm libraries)",
                self.name,
            )
            return []

        if has_nvidia and not has_rocm:
            LOGGER.debug("%s backend GPU auto-detection: selecting --nv", self.name)
            return ['--nv']

        if has_rocm and not has_nvidia:
            LOGGER.debug("%s backend GPU auto-detection: selecting --rocm", self.name)
            return ['--rocm']

        workload_text = self._workload_library_string()
        bound_text = self._bound_files_string()
        command_text = " ".join(map(str, command)).lower()
        env_text = self._env_string()

        nvidia_score = self._vendor_score(NVIDIA_LIBRARY_MARKERS,
                                          workload_text,
                                          bound_text,
                                          command_text,
                                          env_text)
        rocm_score = self._vendor_score(ROCM_LIBRARY_MARKERS,
                                        workload_text,
                                        bound_text,
                                        command_text,
                                        env_text)

        if rocm_score > nvidia_score:
            LOGGER.debug(
                "%s backend GPU auto-detection: dual-stack score nvidia=%d rocm=%d, selecting --rocm",
                self.name,
                nvidia_score,
                rocm_score,
            )
            return ['--rocm']

        # Keep historical behavior on ties or weak evidence: default to --nv.
        LOGGER.debug(
            "%s backend GPU auto-detection: dual-stack score nvidia=%d rocm=%d, selecting --nv",
            self.name,
            nvidia_score,
            rocm_score,
        )
        return ['--nv']

    def _has_nvidia(self, cache_text: str = None):
        # Assume that the proper ldconfig call has been run and that nvidia
        # libraries are listed in the cache.
        if cache_text is None:
            cache_text = self._cache_libraries_string()

        if not self._contains_any(cache_text, NVIDIA_LIBRARY_MARKERS):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True

    def _has_rocm(self, cache_text: str = None):
        # Assume that the proper ldconfig call has been run and that ROCm
        # libraries are listed in the cache.
        if cache_text is None:
            cache_text = self._cache_libraries_string()

        if not self._contains_any(cache_text, ROCM_LIBRARY_MARKERS):
            LOGGER.debug("Disabling ROCm support: no libraries found")
            return False
        return True

    def run(self, command: List[str], overload: bool = True) -> int:
        executable = self._executable()
        if executable is None:
            raise BackendNotAvailableError(self.__class__.__name__)

        container_cmd = [executable, *self._prepare(command, overload)]
        LOGGER.debug("%s backend command: %s", self.name, container_cmd)

        return run_subprocess(container_cmd, env=self.env)
