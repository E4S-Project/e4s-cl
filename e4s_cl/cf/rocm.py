"""
ROCm non-library data handler.

ROCm components lazy-load non-`.so` data files by a path relative to the
runtime library on disk (e.g. HIP/COMGR resolving the `amdgcn/bitcode` LLVM
bitcode used to JIT-compile "blit kernels", relative to `libamdhip64.so`).
W hen such a library is relocated into the container's hostlibs directory, 
this sibling data must be bound into the container as well to avoid opaque 
runtime failures.

This module centralizes all ROCm-specific knowledge needed to handle
ROCm-specific file loading:
 - a registry of known "traced library -> relative asset" relationships,
   used to discover and bind the missing sibling data (see `RocmAsset`);
 - the SONAME denylist for libraries that must never be forced into
   LD_PRELOAD (e.g. ROCm plugins that expect to be dlopen'd lazily);
 - best-effort diagnostics (`AMD_LOG_LEVEL`) for ROCm-backed launches, so
   that any asset dependency this module does not yet know about at least
   surfaces a clear runtime error instead of an opaque crash.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from sotools.libraryset import Library

from e4s_cl.logger import get_logger

LOGGER = get_logger(__name__)

# Libraries that must never be force-preloaded via LD_PRELOAD even when they
# would otherwise be selected as "top level" (unclaimed) members of the
# imported library set.
#
# These are runtime plugins that ROCm/HIP expects to `dlopen` on its own
# terms. librocprofiler-register.so in particular relies on the *loading*
# process resolving an optional `rocprofiler_configure` symbol lazily; when
# it is instead forced into LD_PRELOAD, the dynamic linker performs eager
# binding of that reference and aborts with a fatal "undefined symbol"
# error, which crashes the whole launch (observed as a SIGSEGV in the target
# application once the aborted preload leaves HIP in a broken state).
ROCM_PRELOAD_DENYLIST = ('librocprofiler-register.so', )

# Environment variable used to request verbose HSA/COMGR runtime logging
# from ROCm itself. This is how the missing-bitcode root cause was first
# diagnosed (see rocm_repro/fix-rocm.txt) - injecting a low, default level
# whenever a ROCm-backed launch is detected means any asset dependency this
# module doesn't yet know about at least produces a clear message instead of
# a silent/opaque crash.
_DIAGNOSTIC_ENV_VAR = 'AMD_LOG_LEVEL'
_DIAGNOSTIC_LEVEL_DEFAULT = '1'  # errors only
_DIAGNOSTIC_LEVEL_VERBOSE = '4'  # full HSA/COMGR trace


@dataclass(frozen=True)
class RocmAsset:
    """
    Describes a non-`.so` asset some ROCm component lazy-loads relative to
    a traced runtime library's real path on disk, and how to make it
    available in the container.
    """
    # Human-readable name, used in logs
    name: str
    # SONAME prefixes of libraries whose presence in the imported set means
    # this asset may be required at runtime
    trigger_prefixes: Tuple[str, ...]
    # Path suffixes (relative to a candidate ROCm root), tried in order;
    # may contain a single '*' glob component (e.g. an LLVM version)
    suffixes: Tuple[str, ...]
    # Files expected inside a valid asset directory, used to verify a
    # candidate before trusting it
    markers: Tuple[str, ...]
    # Environment variable that must point ROCm at the bound directory
    env_var: str
    # Subdirectory (under the container's e4s-cl import dir) to bind the
    # asset to, e.g. 'rocm/bitcode'
    container_subdir: str


# Registry of known traced-library -> relative-asset relationships. Seeded
# with the bitcode directory (the only case observed and reproduced so
# far); extend this tuple to cover other lazy-loaded ROCm assets (e.g.
# rocBLAS/MIOpen .kdb kernel caches, hipRTC headers) as they are found.
ROCM_ASSETS: Tuple[RocmAsset, ...] = (
    RocmAsset(
        name='bitcode',
        trigger_prefixes=(
            'libamdhip64.so',
            'libamd_comgr.so',
            'libhsa-runtime64.so',
        ),
        suffixes=(
            'amdgcn/bitcode',
            'lib/llvm/lib/clang/*/lib/amdgcn/bitcode',
            'llvm/lib/clang/*/lib/amdgcn/bitcode',
        ),
        markers=('ockl.bc', 'hip.bc'),
        env_var='HIP_DEVICE_LIB_PATH',
        container_subdir='rocm/bitcode',
    ),
)

# How many parent directories of a traced library to try as a potential
# ROCm install root
_MAX_ANCESTOR_DEPTH = 5


def _is_valid_asset_dir(path: Path, markers: Tuple[str, ...]) -> bool:
    return path.is_dir() and any((path / marker).exists()
                                 for marker in markers)


def _search_root(root: Path, suffixes: Tuple[str, ...],
                 markers: Tuple[str, ...]) -> Optional[Path]:
    """Look for an asset directory under `root` using known suffixes."""
    for suffix in suffixes:
        if '*' in suffix:
            for match in sorted(root.glob(suffix)):
                if _is_valid_asset_dir(match, markers):
                    return match
        else:
            candidate = root / suffix
            if _is_valid_asset_dir(candidate, markers):
                return candidate
    return None


def _hipconfig_rocm_path() -> Optional[Path]:
    try:
        proc = subprocess.run(['hipconfig', '--rocmpath'],
                              capture_output=True,
                              text=True,
                              check=False)
    except OSError:
        return None

    output = proc.stdout.strip()
    if not output:
        return None

    path = Path(output)
    return path if path.is_dir() else None


def _environment_roots(env_var: str) -> Iterable[Path]:
    """Candidate ROCm roots/asset paths advertised via the environment."""
    direct = os.environ.get(env_var)
    if direct:
        yield Path(direct)

    for var in ('ROCM_PATH', 'HIP_PATH'):
        value = os.environ.get(var)
        if value:
            yield Path(value)

    hipconfig_path = _hipconfig_rocm_path()
    if hipconfig_path:
        yield hipconfig_path


def _resolve_via_environment(asset: RocmAsset) -> Optional[Path]:
    for root in _environment_roots(asset.env_var):
        if _is_valid_asset_dir(root, asset.markers):
            return root
        found = _search_root(root, asset.suffixes, asset.markers)
        if found:
            return found
    return None


def _resolve_relative_to_library(library_path: Path,
                                 asset: RocmAsset) -> Optional[Path]:
    """
    Walk up from a traced library's real path looking for a sibling asset
    directory, e.g. `<rocm_root>/lib/llvm/.../amdgcn/bitcode` relative to
    `<rocm_root>/lib/libamdhip64.so`.
    """
    try:
        real_path = library_path.resolve()
    except OSError:
        real_path = library_path

    ancestors = [real_path.parent, *list(real_path.parent.parents)]

    for ancestor in ancestors[:_MAX_ANCESTOR_DEPTH]:
        found = _search_root(ancestor, asset.suffixes, asset.markers)
        if found:
            return found
    return None


def find_asset_dir(library_path: Path, asset: RocmAsset) -> Optional[Path]:
    """
    Find the host directory holding `asset`, preferring a location
    resolved relative to `library_path` (the real host path of a traced
    ROCm library depending on it), and falling back to environment/tooling
    based discovery (`asset.env_var`, `ROCM_PATH`, `hipconfig --rocmpath`).
    """
    found = _resolve_relative_to_library(library_path, asset)
    if found:
        return found

    return _resolve_via_environment(asset)


class RocmDiscovery(NamedTuple):
    """
    Result of inspecting a launch's imported library set for ROCm assets.
    """
    # True if any library in the set is known to depend on a registered
    # ROCm asset, whether or not that asset could actually be located.
    # Callers use this to decide whether a launch is "ROCm-backed" at all
    # (e.g. to gate diagnostics), independently of resolution success.
    detected: bool
    # (host_dir, env_var, container_subdir) for each asset resolved
    resolved: List[Tuple[Path, str, str]]
    # Names of assets that were triggered but could not be located
    missing: List[str]


def discover_rocm_assets(libraries: Iterable[Library]) -> RocmDiscovery:
    """
    Inspect the set of libraries imported for a launch and, for each
    registered ROCm asset whose trigger library is present, try to locate
    the host directory holding it.
    """
    names = [Path(lib.binary_path).name for lib in libraries]
    paths = [Path(lib.binary_path) for lib in libraries]

    detected = False
    resolved: List[Tuple[Path, str, str]] = []
    missing: List[str] = []

    for asset in ROCM_ASSETS:
        matches = [
            path for name, path in zip(names, paths)
            if name.startswith(asset.trigger_prefixes)
        ]
        if not matches:
            continue

        detected = True

        found = None
        for library_path in matches:
            found = find_asset_dir(library_path, asset)
            if found:
                break

        if found:
            LOGGER.debug("Found ROCm '%s' asset directory '%s' for '%s'",
                        asset.name, found, matches[0])
            resolved.append((found, asset.env_var, asset.container_subdir))
        else:
            missing.append(asset.name)
            LOGGER.warning(
                "Detected ROCm library '%s' but could not locate its '%s' "
                "asset directory; ROCm may fail to initialize in the "
                "container. Set %s or ROCM_PATH on the host to help "
                "e4s-cl locate it.", matches[0], asset.name, asset.env_var)

    return RocmDiscovery(detected=detected, resolved=resolved, missing=missing)


def diagnostic_env(discovery: RocmDiscovery,
                   verbose: bool,
                   existing_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Return environment variable overrides to enable ROCm's own runtime
    diagnostics for a ROCm-backed launch, so that any asset dependency not
    covered by `ROCM_ASSETS` at least surfaces a clear error instead of an
    opaque crash - as opposed to requiring a user to manually discover and
    set `SINGULARITYENV_AMD_LOG_LEVEL=4` after the fact.

    Does nothing if no ROCm library was detected, or if the launch/host
    environment already sets the diagnostic variable explicitly.
    """
    if not discovery.detected:
        return {}

    if os.environ.get(_DIAGNOSTIC_ENV_VAR):
        return {}

    if existing_env and _DIAGNOSTIC_ENV_VAR in existing_env:
        return {}

    level = _DIAGNOSTIC_LEVEL_VERBOSE if (
        verbose or discovery.missing) else _DIAGNOSTIC_LEVEL_DEFAULT

    return {_DIAGNOSTIC_ENV_VAR: level}
