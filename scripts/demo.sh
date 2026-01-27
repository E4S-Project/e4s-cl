#!/usr/bin/env bash
# High-level e4s-cl validation script
# - Starts from a clean, local build of e4s-cl
# - Uses apptainer + MPI-enabled container image
# - Primary focus: run a container-built MPI app using the host MPI
# - Also captures host baseline and optional in-container baseline
# - Compares host vs e4s-cl launch vs container-only performance
#
# Notes:
# - Primary use case: portable container apps should leverage optimized host MPI.
# - Reverse (host-built app inside container) is useful but secondary.
# - Cross-scheduler support (host and container differ) is future work.
#
# Usage:
#   ./scripts/demo.sh [options]
#   ./scripts/demo.sh --help
#
# Host MPI notes:
# - Typical host MPI stacks: MPICH, Open MPI, MVAPICH2, Intel MPI, Cray MPICH.
# - If installing with Spack, ensure mpicc/mpirun are in PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

E4S_CL_IMAGE=""
E4S_CL_PROFILE_NAME="HOST_MPI"
E4S_CL_MPI_PROCS="2"
E4S_CL_OSU_URL="https://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-5.9.tar.gz"
E4S_CL_MODE="full"
E4S_CL_TAG=""
E4S_CL_WORKDIR="${REPO_ROOT}/_e4scl_test"
E4S_CL_CACHE_DIR="${REPO_ROOT}/_e4scl_cache"
E4S_CL_KEEP_WORKDIR="1"
E4S_CL_BUILD_IMAGE="0"
E4S_CL_IMAGE_OUTPUT="${E4S_CL_CACHE_DIR}/e4s-cl-mpich.sif"
E4S_CL_IMAGE_DEF=""
E4S_CL_REBUILD_IMAGE="0"
E4S_CL_APPTAINER_BUILD_ARGS=""
E4S_CL_RUN_HOST_BASELINE="1"
E4S_CL_RUN_CONTAINER_BASELINE="0"
E4S_CL_PRUNE_INTEL_OPENCL="0"
E4S_CL_SKIP_PROFILE_DETECT="0"
E4S_CL_WI4MPI_CFLAGS="-Wno-error=implicit-function-declaration -Wno-error=incompatible-pointer-types -Wno-error=format -Wno-error=int-conversion -Wno-error=return-type -include string.h -include sys/time.h"
E4S_CL_APPTAINER_EXEC_OPTIONS=""
E4S_CL_CONTAINER_DIR="/tmp/.e4s-cl"
E4S_CL_HOST_MPI=""
E4S_CL_HOST_MPIRUN=""
E4S_CL_LAUNCHER=""
E4S_CL_SCHEDULER=""
E4S_CL_E4SCL_LAUNCH_ARGS=""
E4S_CL_TIMEOUT_DURATION="60s"

log() { printf "[e4s-cl-test] %s\n" "$*"; }
fail() { printf "[e4s-cl-test] ERROR: %s\n" "$*" >&2; exit 1; }

DOC_TODO_FILE="${REPO_ROOT}/documentation.TODO"
doc_todo() {
  local note="$1"
  if [[ ! -f "${DOC_TODO_FILE}" ]]; then
    printf "# Documentation TODOs (auto-collected)\n" > "${DOC_TODO_FILE}"
  fi
  if ! grep -Fq "${note}" "${DOC_TODO_FILE}"; then
    printf -- "- %s\n" "${note}" >> "${DOC_TODO_FILE}"
  fi
}

usage() {
  cat <<EOF
High-level e4s-cl validation script

Usage:
  ./scripts/demo.sh [options]

Options:
  --image <path|uri>           Apptainer image path (.sif) or URI (docker://...) (default: none)
  --build-image                Build a local MPICH apptainer image (default: off)
  --image-output <path>        Output image path (default: _e4scl_cache_<tag>/e4s-cl-mpich-<tag>.sif)
  --image-def <path>           Custom apptainer definition file (default: auto-generated)
  --rebuild-image              Force rebuild of image when --build-image is set (default: off)
  --apptainer-build-args <arg> Extra args for apptainer build (default: --fakeroot)
  --profile-name <name>        Profile name to use (default: HOST_MPI)
  --mpi-procs <n>              MPI ranks (default: 2)
  --osu-url <url>              OSU benchmarks tarball URL (default: https://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-5.9.tar.gz)
  --mode <light|full>          Light: latency/bw tests (shorter). Full: adds allreduce + full range (default: full)
  --tag <name>                 Artifact tag used for work/cache paths (default: auto)
  --workdir <path>             Working directory (default: _e4scl_test_<tag>)
  --cache-dir <path>           Cache directory (default: _e4scl_cache_<tag>)
  --clean-workdir              Delete workdir on exit (default: off)
  --host-baseline <on|off>     Run host-only baseline (default: on)
  --container-baseline <on|off> Run container-only baseline (default: off)
  --no-prune-intel-opencl      Disable workaround that prunes Intel/OpenCL libs from profile (default: pruning enabled)
  --skip-profile-detect        Skip profile detect if profile already has bindings (default: off)
  --wi4mpi-cflags "..."         Extra C/C++ flags for Wi4MPI build (default: relax GCC 14 errors)
  --apptainer-exec-options "..." Extra apptainer exec options (default: none)
  --container-dir <path>       Container data dir (default: /tmp/.e4s-cl)
  --host-mpicc <path>          Override host mpicc (default: auto-detect)
  --host-mpirun <path>         Override host mpirun/mpiexec (default: auto-detect)
  --launcher <cmd>             Force launcher (mpirun or srun) (default: auto-detect)
  --scheduler <name>           If "slurm", use srun when available (default: none)
  --e4scl-launch-args "..."     Extra args for e4s-cl launch (default: none)
  --timeout <duration>         Timeout for MPI runs (default: 60s)
  --check                      Check environment prerequisites and exit
  -h, --help                   Show help

Examples:
  ./scripts/demo.sh --image /path/to/mpi.sif --mode light
  ./scripts/demo.sh --build-image --mode light --host-baseline off
  ./scripts/demo.sh --image docker://ecpe4s/e4s-mpi-cpu-x86_64:v4.3.1-1762472545 --mode light
EOF
}

parse_bool() {
  case "${1,,}" in
    1|true|yes|on) echo "1" ;;
    0|false|no|off) echo "0" ;;
    *) fail "Invalid boolean value: $1 (use on/off, true/false, 1/0)" ;;
  esac
}

sanitize_tag() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's#[^a-z0-9._-]+#-#g' | sed -E 's/^-+|-+$//g'
}

derive_tag() {
  local base=""
  local suffix="-${E4S_CL_MODE}-np${E4S_CL_MPI_PROCS}"
  if [[ -n "${E4S_CL_IMAGE}" ]]; then
    base="${E4S_CL_IMAGE##*/}"
    base="${base%.sif}"
    base="${base//:/-}"
    # Avoid duplicating the suffix if it's already in the image name
    if [[ "${base}" == *"${suffix}" ]]; then
      base="${base%"${suffix}"}"
    fi
  elif [[ "${E4S_CL_BUILD_IMAGE}" == "1" ]]; then
    base="local-mpich"
  else
    base="default"
  fi
  echo "${base}${suffix}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) E4S_CL_IMAGE="$2"; shift 2 ;;
    --build-image) E4S_CL_BUILD_IMAGE="1"; shift ;;
    --image-output) E4S_CL_IMAGE_OUTPUT="$2"; shift 2 ;;
    --image-def) E4S_CL_IMAGE_DEF="$2"; shift 2 ;;
    --rebuild-image) E4S_CL_REBUILD_IMAGE="1"; shift ;;
    --apptainer-build-args) E4S_CL_APPTAINER_BUILD_ARGS="$2"; shift 2 ;;
    --profile-name) E4S_CL_PROFILE_NAME="$2"; shift 2 ;;
    --mpi-procs) E4S_CL_MPI_PROCS="$2"; shift 2 ;;
    --osu-url) E4S_CL_OSU_URL="$2"; shift 2 ;;
    --mode) E4S_CL_MODE="$2"; shift 2 ;;
    --tag) E4S_CL_TAG="$2"; shift 2 ;;
    --workdir) E4S_CL_WORKDIR="$2"; shift 2 ;;
    --cache-dir) E4S_CL_CACHE_DIR="$2"; shift 2 ;;
    --clean-workdir) E4S_CL_KEEP_WORKDIR="0"; shift ;;
    --host-baseline) E4S_CL_RUN_HOST_BASELINE="$(parse_bool "$2")"; shift 2 ;;
    --container-baseline) E4S_CL_RUN_CONTAINER_BASELINE="$(parse_bool "$2")"; shift 2 ;;
    --no-prune-intel-opencl) E4S_CL_PRUNE_INTEL_OPENCL="0"; shift ;;
    --skip-profile-detect) E4S_CL_SKIP_PROFILE_DETECT="1"; shift ;;
    --wi4mpi-cflags) E4S_CL_WI4MPI_CFLAGS="$2"; shift 2 ;;
    --apptainer-exec-options) E4S_CL_APPTAINER_EXEC_OPTIONS="$2"; shift 2 ;;
    --container-dir) E4S_CL_CONTAINER_DIR="$2"; shift 2 ;;
    --run-host-baseline) E4S_CL_RUN_HOST_BASELINE="1"; shift ;;
    --skip-host-baseline) E4S_CL_RUN_HOST_BASELINE="0"; shift ;;
    --run-container-baseline) E4S_CL_RUN_CONTAINER_BASELINE="1"; shift ;;
    --skip-container-baseline) E4S_CL_RUN_CONTAINER_BASELINE="0"; shift ;;
    --host-mpicc) E4S_CL_HOST_MPI="$2"; shift 2 ;;
    --host-mpirun) E4S_CL_HOST_MPIRUN="$2"; shift 2 ;;
    --launcher) E4S_CL_LAUNCHER="$2"; shift 2 ;;
    --scheduler) E4S_CL_SCHEDULER="$2"; shift 2 ;;
    --e4scl-launch-args) E4S_CL_E4SCL_LAUNCH_ARGS="$2"; shift 2 ;;
    --timeout) E4S_CL_TIMEOUT_DURATION="$2"; shift 2 ;;
    --check) E4S_CL_ONLY_CHECK="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown argument: $1 (use --help)" ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

check_cmd() {
  command -v "$1" >/dev/null 2>&1
}

if [[ "${E4S_CL_ONLY_CHECK:-0}" == "1" ]]; then
  log "Checking environment..."
  
  MISSING=0
  
  log "Checking Python..."
  if check_cmd python3; then
     log "  Found: $(command -v python3) ($(python3 --version))"
  else
     log "  MISSING: python3"
     MISSING=1
  fi
  
  log "Checking Container Runtime..."
  if check_cmd apptainer; then
     log "  Found: $(command -v apptainer) ($(apptainer --version))"
  elif check_cmd singularity; then
     log "  Found: $(command -v singularity) ($(singularity --version))"
  else
     log "  MISSING: apptainer or singularity"
     MISSING=1
  fi
  
  log "Checking MPI..."
  if check_cmd mpicc; then
     log "  Found: $(command -v mpicc)"
  else
     log "  MISSING: mpicc (common in default environments, but needed for tests)"
     MISSING=1
  fi
  
  if check_cmd mpirun; then
     log "  Found: $(command -v mpirun)"
  else
     log "  MISSING: mpirun"
     MISSING=1
  fi
  
  log "Checking Utilities..."
  for tool in curl tar make gcc timeout; do
    if check_cmd "$tool"; then
       log "  Found: $tool"
    else
       log "  MISSING: $tool"
       MISSING=1
    fi
  done
  
  if [[ "$MISSING" -eq 1 ]]; then
     fail "One or more prerequisites missing."
  else
     log "Environment looks good!"
     exit 0
  fi
fi

DEFAULT_WORKDIR="${REPO_ROOT}/_e4scl_test"
DEFAULT_CACHE_DIR="${REPO_ROOT}/_e4scl_cache"
if [[ -z "${E4S_CL_TAG}" ]]; then
  E4S_CL_TAG="$(sanitize_tag "$(derive_tag)")"
fi
if [[ "${E4S_CL_WORKDIR}" == "${DEFAULT_WORKDIR}" ]]; then
  E4S_CL_WORKDIR="${DEFAULT_WORKDIR}_${E4S_CL_TAG}"
fi
if [[ "${E4S_CL_CACHE_DIR}" == "${DEFAULT_CACHE_DIR}" ]]; then
  E4S_CL_CACHE_DIR="${DEFAULT_CACHE_DIR}_${E4S_CL_TAG}"
fi
if [[ "${E4S_CL_IMAGE_OUTPUT}" == "${DEFAULT_CACHE_DIR}/e4s-cl-mpich.sif" ]]; then
  E4S_CL_IMAGE_OUTPUT="${E4S_CL_CACHE_DIR}/e4s-cl-mpich-${E4S_CL_TAG}.sif"
fi

run_timed() {
  local label="$1"
  shift
  local cmd=("$@")
  local out_file="${E4S_CL_WORKDIR}/timing.dat"

  log "Running [${label}]..."
  # Use python for distinct wall-clock measurement
  local start
  start=$(python3 -c 'import time; print(time.time())')

  set +e
  timeout "${E4S_CL_TIMEOUT_DURATION}" "${cmd[@]}"
  local ret=$?
  set -e

  if [[ $ret -eq 124 ]]; then
    fail "Command timed out (${E4S_CL_TIMEOUT_DURATION}): ${cmd[*]}"
  elif [[ $ret -ne 0 ]]; then
    fail "Command failed (exit $ret): ${cmd[*]}"
  fi

  local end
  end=$(python3 -c 'import time; print(time.time())')
  local duration
  duration=$(python3 -c "print(f'{${end} - ${start}:.3f}')")

  # Use flock or simple append (pipe serialization usually handles simple appends)
  printf "%s %s\n" "${label}" "${duration}" >> "${out_file}"
}

detect_mpi_family() {
  local text="$1"
  local lowered
  lowered=$(echo "$text" | tr 'A-Z' 'a-z')
  if echo "$lowered" | grep -q "open mpi"; then
    echo "openmpi"
  elif echo "$lowered" | grep -q "mvapich"; then
    echo "mvapich"
  elif echo "$lowered" | grep -q "intel"; then
    echo "intelmpi"
  elif echo "$lowered" | grep -q "cray mpich"; then
    echo "mpich"
  elif echo "$lowered" | grep -q "hydra"; then
    echo "mpich"
  elif echo "$lowered" | grep -q "mpich"; then
    echo "mpich"
  else
    echo ""
  fi
}

log "Validating prerequisites"
require_cmd python3
require_cmd curl
require_cmd tar
require_cmd make
require_cmd gcc

if check_cmd apptainer; then
  CONTAINER_CMD="apptainer"
  log "Using Container Runtime: apptainer"
elif check_cmd singularity; then
  CONTAINER_CMD="singularity"
  log "Using Container Runtime: singularity"
else
  fail "Neither apptainer nor singularity found. Install one and try again."
fi

if [[ "${E4S_CL_BUILD_IMAGE}" == "1" ]]; then
  mkdir -p "${E4S_CL_CACHE_DIR}"
  if [[ -z "${E4S_CL_IMAGE}" ]]; then
    E4S_CL_IMAGE="${E4S_CL_IMAGE_OUTPUT}"
  fi
  if [[ "${E4S_CL_REBUILD_IMAGE}" == "1" || ! -f "${E4S_CL_IMAGE}" ]]; then
    log "Building local MPICH container image: ${E4S_CL_IMAGE}"
    if [[ -z "${E4S_CL_IMAGE_DEF}" ]]; then
      HOST_ARCH="$(uname -m)"
      case "${HOST_ARCH}" in
        x86_64|amd64) BASE_IMAGE="ubuntu:22.04" ;;
        aarch64|arm64) BASE_IMAGE="arm64v8/ubuntu:22.04" ;;
        ppc64le) BASE_IMAGE="ppc64le/ubuntu:22.04" ;;
        *)
          BASE_IMAGE="ubuntu:22.04"
          log "Unknown arch '${HOST_ARCH}', defaulting to ${BASE_IMAGE}"
          doc_todo "Local image build defaults to ubuntu:22.04 for unknown arch (${HOST_ARCH}); document supported arches."
          ;;
      esac
      E4S_CL_IMAGE_DEF="${E4S_CL_CACHE_DIR}/e4s-cl-mpich-${E4S_CL_TAG}.def"
      cat > "${E4S_CL_IMAGE_DEF}" <<EOF
Bootstrap: docker
From: ${BASE_IMAGE}

%post
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    mpich libmpich-dev \
    build-essential gcc g++ gfortran make pkg-config file \
    curl ca-certificates tar
  apt-get clean
  rm -rf /var/lib/apt/lists/*

%environment
  export PATH=/usr/bin:\$PATH
EOF
    fi

    if [[ -z "${E4S_CL_APPTAINER_BUILD_ARGS}" ]]; then
      E4S_CL_APPTAINER_BUILD_ARGS="--fakeroot"
    fi
    ${CONTAINER_CMD} build ${E4S_CL_APPTAINER_BUILD_ARGS} "${E4S_CL_IMAGE}" "${E4S_CL_IMAGE_DEF}"
  fi
fi

[[ -n "${E4S_CL_IMAGE}" ]] || fail "--image is required or enable --build-image"
if [[ "${E4S_CL_IMAGE}" != docker://* && "${E4S_CL_IMAGE}" != library://* ]]; then
  [[ -f "${E4S_CL_IMAGE}" ]] || fail "E4S_CL_IMAGE not found: ${E4S_CL_IMAGE}"
fi

# Host MPI detection
HOST_MPICC="${E4S_CL_HOST_MPI:-$(command -v mpicc || true)}"
HOST_MPIRUN="${E4S_CL_HOST_MPIRUN:-$(command -v mpirun || command -v mpiexec || true)}"
[[ -n "${HOST_MPICC}" ]] || fail "Host MPI compiler not found (mpicc)"
[[ -n "${HOST_MPIRUN}" ]] || fail "Host MPI launcher not found (mpirun or mpiexec)"

log "Container Runtime: $CONTAINER_CMD"
log "Host MPI compiler: ${HOST_MPICC}"\
"$("${HOST_MPICC}" --version | head -n 1 || true)"
log "Host MPI launcher: ${HOST_MPIRUN}"\
"$("${HOST_MPIRUN}" --version | head -n 1 || true)"

LAUNCHER_BIN="${E4S_CL_LAUNCHER:-}"
if [[ -z "${LAUNCHER_BIN}" && "${E4S_CL_SCHEDULER}" == "slurm" ]]; then
  LAUNCHER_BIN="$(command -v srun || true)"
fi
if [[ -z "${LAUNCHER_BIN}" ]]; then
  LAUNCHER_BIN="${HOST_MPIRUN}"
fi

if [[ "${LAUNCHER_BIN##*/}" == "srun" ]]; then
  LAUNCHER_ARGS=("-n" "${E4S_CL_MPI_PROCS}")
else
  LAUNCHER_ARGS=("-np" "${E4S_CL_MPI_PROCS}")
fi

HOST_MPI_VERSION="$(${HOST_MPIRUN} --version 2>/dev/null | head -n 2 || true)"
HOST_MPI_FAMILY="$(detect_mpi_family "${HOST_MPI_VERSION}")"
CONTAINER_MPI_VERSION="$(${CONTAINER_CMD} exec "${E4S_CL_IMAGE}" mpirun --version 2>/dev/null | head -n 2 || true)"
if [[ -z "$(detect_mpi_family "${CONTAINER_MPI_VERSION}")" ]]; then
  CONTAINER_MPI_VERSION+=$'\n'"$(${CONTAINER_CMD} exec "${E4S_CL_IMAGE}" mpichversion 2>/dev/null | head -n 2 || true)"
fi
CONTAINER_MPI_FAMILY="$(detect_mpi_family "${CONTAINER_MPI_VERSION}")"

log "Detected host MPI family: ${HOST_MPI_FAMILY:-unknown}"
log "Detected container MPI family: ${CONTAINER_MPI_FAMILY:-unknown}"

# Best-effort heads-up for the Open MPI CMA user-namespace warning that shows up
# when the host MPI is Open MPI and we run ranks inside an apptainer/singularity
# user namespace (non-setuid). In that case the `vader` BTL drops to memcpy and
# emits a cma-different-user-namespace warning; bandwidth/latency dip is normal.
if [[ "${HOST_MPI_FAMILY}" == "openmpi" && "${CONTAINER_CMD}" =~ ^(apptainer|singularity)$ ]]; then
  log "INFO: Host Open MPI under ${CONTAINER_CMD} often runs ranks in separate user namespaces;"
  log "INFO: Open MPI's vader BTL will warn about CMA and fall back to memcpy (small perf drop expected)."
  log "INFO: If you need to avoid it, run with setuid ${CONTAINER_CMD}, share the user namespace, or bind a helpfile path for clearer messaging."
fi

E4SCL_LAUNCH_ARGS=()
if [[ -n "${E4S_CL_E4SCL_LAUNCH_ARGS}" ]]; then
  read -r -a E4SCL_LAUNCH_ARGS <<< "${E4S_CL_E4SCL_LAUNCH_ARGS}"
fi

NEEDS_TRANSLATION="0"
if printf '%s\n' "${E4SCL_LAUNCH_ARGS[@]}" | grep -q -- "--from"; then
  NEEDS_TRANSLATION="1"
elif [[ -n "${HOST_MPI_FAMILY}" && -n "${CONTAINER_MPI_FAMILY}" && "${HOST_MPI_FAMILY}" != "${CONTAINER_MPI_FAMILY}" ]]; then
  log "MPI mismatch detected (host=${HOST_MPI_FAMILY}, container=${CONTAINER_MPI_FAMILY}); enabling Wi4MPI translation"
  E4SCL_LAUNCH_ARGS=("--from" "${CONTAINER_MPI_FAMILY}" "${E4SCL_LAUNCH_ARGS[@]}")
  NEEDS_TRANSLATION="1"
  doc_todo "e4s-cl requires explicit --from when container MPI differs; add guidance to auto-detect and pass --from."
fi

log "Step 1: Setting up e4s-cl. Using a local virtual environment and editable install to ensure the latest code is used."
if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  python3 -m venv "${REPO_ROOT}/.venv"
fi
"${REPO_ROOT}/.venv/bin/python" -m pip install -U pip
"${REPO_ROOT}/.venv/bin/python" -m pip install -e "${REPO_ROOT}"

E4S_CL_BIN="${REPO_ROOT}/.venv/bin/e4s-cl"
[[ -x "${E4S_CL_BIN}" ]] || fail "e4s-cl not installed in venv"

if [[ "${NEEDS_TRANSLATION}" == "1" ]]; then
  log "Wi4MPI translation required; e4s-cl will install Wi4MPI during launch if missing"
  if [[ -n "${E4S_CL_WI4MPI_CFLAGS}" ]]; then
    log "CONFIG: injecting Wi4MPI build flags to ensure compatibility (e.g., GCC 14)"
    log "CONFIG: CFLAGS/CXXFLAGS=${E4S_CL_WI4MPI_CFLAGS}"
    export CFLAGS="${E4S_CL_WI4MPI_CFLAGS} ${CFLAGS:-}"
    export CXXFLAGS="${E4S_CL_WI4MPI_CFLAGS} ${CXXFLAGS:-}"
  fi
fi

if [[ -n "${E4S_CL_APPTAINER_EXEC_OPTIONS}" ]]; then
  # Useful for complex container setups
  log "CONFIG: setting E4S_CL_APPTAINER_EXEC_OPTIONS=${E4S_CL_APPTAINER_EXEC_OPTIONS}"
  export E4S_CL_APPTAINER_EXEC_OPTIONS="${E4S_CL_APPTAINER_EXEC_OPTIONS}"
fi

if [[ -n "${E4S_CL_CONTAINER_DIR}" ]]; then
  # Use a specific container directory relative to host environment
  log "CONFIG: setting E4S_CL_CONTAINER_DIR=${E4S_CL_CONTAINER_DIR}"
  export E4S_CL_CONTAINER_DIR="${E4S_CL_CONTAINER_DIR}"
fi

log "Preparing workdir: ${E4S_CL_WORKDIR}"
mkdir -p "${E4S_CL_WORKDIR}"
mkdir -p "${E4S_CL_CACHE_DIR}"

log "Fetching OSU benchmarks"
OSU_TARBALL="${E4S_CL_CACHE_DIR}/osu.tar.gz"
OSU_SRC_DIR="${E4S_CL_WORKDIR}/osu"
OSU_META_FILE="${E4S_CL_WORKDIR}/osu.meta"
if [[ ! -f "${OSU_TARBALL}" || ! -f "${OSU_META_FILE}" ]]; then
  curl -L "${E4S_CL_OSU_URL}" -o "${OSU_TARBALL}"
  rm -rf "${OSU_SRC_DIR}"
elif ! grep -Fq "osu_url=${E4S_CL_OSU_URL}" "${OSU_META_FILE}"; then
  curl -L "${E4S_CL_OSU_URL}" -o "${OSU_TARBALL}"
  rm -rf "${OSU_SRC_DIR}"
fi
if [[ ! -d "${OSU_SRC_DIR}" ]]; then
  mkdir -p "${OSU_SRC_DIR}"
  tar -xzf "${OSU_TARBALL}" -C "${OSU_SRC_DIR}" --strip-components=1
fi
printf "osu_url=%s\n" "${E4S_CL_OSU_URL}" > "${OSU_META_FILE}"

if [[ "${E4S_CL_MODE}" == "light" ]]; then
  OSU_BENCHES=("pt2pt/osu_latency" "pt2pt/osu_bw")
  OSU_ARGS=("-x" "10" "-i" "100" "-m" "8:1024")
else
  OSU_BENCHES=("pt2pt/osu_latency" "pt2pt/osu_bw" "collective/osu_allreduce")
  OSU_ARGS=()
fi

if [[ "${E4S_CL_MPI_PROCS}" != "2" ]]; then
  if printf '%s\n' "${OSU_BENCHES[@]}" | grep -q "pt2pt/osu_"; then
    log "NOTE: pt2pt OSU benchmarks require exactly 2 processes (current: ${E4S_CL_MPI_PROCS})"
  fi
fi

log "Step 2: Building Host Benchmarks. We compile OSU benchmarks on the host to 1) check host MPI health, 2) set a performance baseline, and 3) provide a binary for e4s-cl to analyze."
OSU_HOST_PREFIX="${E4S_CL_WORKDIR}/osu-host"
OSU_HOST_META="${OSU_HOST_PREFIX}/.build-meta"
HOST_MPICC_VERSION="$(${HOST_MPICC} --version | head -n 1 || true)"
REBUILD_HOST_OSU="0"
if [[ ! -d "${OSU_HOST_PREFIX}" || ! -f "${OSU_HOST_META}" ]]; then
  REBUILD_HOST_OSU="1"
elif ! grep -Fq "mpicc=${HOST_MPICC}" "${OSU_HOST_META}"; then
  REBUILD_HOST_OSU="1"
elif ! grep -Fq "mpicc_version=${HOST_MPICC_VERSION}" "${OSU_HOST_META}"; then
  REBUILD_HOST_OSU="1"
elif ! grep -Fq "osu_url=${E4S_CL_OSU_URL}" "${OSU_HOST_META}"; then
  REBUILD_HOST_OSU="1"
fi

if [[ "${REBUILD_HOST_OSU}" == "1" ]]; then
  log "(Re)building host OSU benchmarks"
  rm -rf "${OSU_HOST_PREFIX}"
  mkdir -p "${OSU_HOST_PREFIX}"
  (
    cd "${OSU_SRC_DIR}"
    ./configure CC="${HOST_MPICC}" --prefix="${OSU_HOST_PREFIX}"
    make -j
    make install
  )
  printf "mpicc=%s\nmpicc_version=%s\nosu_url=%s\n" "${HOST_MPICC}" "${HOST_MPICC_VERSION}" "${E4S_CL_OSU_URL}" > "${OSU_HOST_META}"
else
  log "Reusing host OSU benchmarks: ${OSU_HOST_PREFIX}"
fi

if [[ "${E4S_CL_RUN_HOST_BASELINE}" == "1" ]]; then
  log "Step 2b: Running baseline host MPI benchmarks. This confirms the host MPI works and provides reference numbers."
  for bench in "${OSU_BENCHES[@]}"; do
    bench_name="$(basename "${bench}")"
    out_file="${E4S_CL_WORKDIR}/host_${bench_name}.txt"
    run_timed "host_${bench_name}" "${LAUNCHER_BIN}" "${LAUNCHER_ARGS[@]}" \
      "${OSU_HOST_PREFIX}/libexec/osu-micro-benchmarks/mpi/${bench}" \
      "${OSU_ARGS[@]}" | tee "${out_file}"
  done
fi

log "Step 3: Configuring e4s-cl Profile. A 'profile' stores metadata about the container backend, image, and the host libraries we want to inject."
if ! "${E4S_CL_BIN}" profile create "${E4S_CL_PROFILE_NAME}" --backend "${CONTAINER_CMD}" --image "${E4S_CL_IMAGE}"; then
  log "Profile exists, updating image/backend"
  "${E4S_CL_BIN}" profile edit --backend "${CONTAINER_CMD}" --image "${E4S_CL_IMAGE}"
fi
"${E4S_CL_BIN}" profile select "${E4S_CL_PROFILE_NAME}"

# Validate detection results; if empty, retry once and fail early with guidance.
# This mirrors how a user would re-run detection when the profile isn't populated.
profile_has_bindings() {
  local output
  output="$(${E4S_CL_BIN} profile show)"
  if echo "${output}" | awk '/^Bound libraries:/{inlib=1; next} /^Bound files:/{inlib=0} inlib && /^ - /{print}' | grep -q .; then
    return 0
  fi
  if echo "${output}" | awk '/^Bound files:/{infiles=1; next} infiles && /^ - /{print}' | grep -q .; then
    return 0
  fi
  return 1
}

if [[ "${E4S_CL_SKIP_PROFILE_DETECT}" == "1" ]]; then
  if profile_has_bindings; then
    log "Skipping profile detect (--skip-profile-detect); using existing profile bindings"
  else
    log "WARNING: --skip-profile-detect specified but profile has no bindings; running detect anyway"
    run_timed "detect" "${E4S_CL_BIN}" profile detect "${LAUNCHER_BIN}" "${LAUNCHER_ARGS[@]}" -- "${OSU_HOST_PREFIX}/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency"
  fi
else
  log "Step 4: Profile Analysis. e4s-cl traces the execution of a host binary to find all shared libraries and files needed to run MPI on this system."
  run_timed "detect" "${E4S_CL_BIN}" profile detect "${LAUNCHER_BIN}" "${LAUNCHER_ARGS[@]}" -- "${OSU_HOST_PREFIX}/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency"
fi

if ! profile_has_bindings; then
  log "Profile detect produced no bound libraries/files; retrying once"
  run_timed "detect_retry" "${E4S_CL_BIN}" profile detect "${LAUNCHER_BIN}" "${LAUNCHER_ARGS[@]}" -- "${OSU_HOST_PREFIX}/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency"
  if ! profile_has_bindings; then
    fail "Profile detect produced no libraries/files. Verify launcher and MPI environment, then retry."
  fi
fi

log "Step 5: Building Container Benchmarks. We compile the same benchmarks *inside* the container against the Container's MPI to demonstrate ABI compatibility or translation."
OSU_CONT_PREFIX="${E4S_CL_WORKDIR}/osu-container"
OSU_CONT_META="${OSU_CONT_PREFIX}/.build-meta"
REBUILD_CONT_OSU="0"
if [[ ! -d "${OSU_CONT_PREFIX}" || ! -f "${OSU_CONT_META}" ]]; then
  REBUILD_CONT_OSU="1"
elif ! grep -Fq "container_mpi=${CONTAINER_MPI_VERSION}" "${OSU_CONT_META}"; then
  REBUILD_CONT_OSU="1"
elif ! grep -Fq "osu_url=${E4S_CL_OSU_URL}" "${OSU_CONT_META}"; then
  REBUILD_CONT_OSU="1"
fi

if [[ "${REBUILD_CONT_OSU}" == "1" ]]; then
  log "(Re)building container OSU benchmarks"
  rm -rf "${OSU_CONT_PREFIX}"
  mkdir -p "${OSU_CONT_PREFIX}"
  ${CONTAINER_CMD} exec -B "${E4S_CL_WORKDIR}:/work" -B "${E4S_CL_CACHE_DIR}:/cache" "${E4S_CL_IMAGE}" bash -lc "\
    set -euo pipefail; \
    cd /work; \
    rm -rf osu-container-build && mkdir osu-container-build; \
    tar -xzf /cache/osu.tar.gz -C osu-container-build --strip-components=1; \
    cd osu-container-build; \
    ./configure CC=mpicc --prefix=/work/osu-container; \
    make -j; \
    make install; \
  "
  printf "container_mpi=%s\nosu_url=%s\n" "${CONTAINER_MPI_VERSION}" "${E4S_CL_OSU_URL}" > "${OSU_CONT_META}"
else
  log "Reusing container OSU benchmarks: ${OSU_CONT_PREFIX}"
fi

log "Step 6: MAIN TEST. Running the container-compiled binary using the Host's MPI. e4s-cl handles the library injection and launcher wrapping."
for bench in "${OSU_BENCHES[@]}"; do
  bench_name="$(basename "${bench}")"
  out_file="${E4S_CL_WORKDIR}/e4scl_${bench_name}.txt"
  run_timed "e4scl_${bench_name}" "${E4S_CL_BIN}" launch "${E4SCL_LAUNCH_ARGS[@]}" "${LAUNCHER_BIN}" "${LAUNCHER_ARGS[@]}" \
    "${OSU_CONT_PREFIX}/libexec/osu-micro-benchmarks/mpi/${bench}" \
    "${OSU_ARGS[@]}" | tee "${out_file}"
done

if [[ "${E4S_CL_RUN_CONTAINER_BASELINE}" == "1" ]]; then
  log "Step 7: Container Baseline. Running benchmarks using the Container's unoptimized MPI (if enabled). This compares 'native container' vs 'e4s-cl host MPI'."
  for bench in "${OSU_BENCHES[@]}"; do
    bench_name="$(basename "${bench}")"
    out_file="${E4S_CL_WORKDIR}/container_${bench_name}.txt"
    run_timed "container_${bench_name}" ${CONTAINER_CMD} exec -B "${E4S_CL_WORKDIR}:/work" "${E4S_CL_IMAGE}" bash -lc "\
      mpirun -np ${E4S_CL_MPI_PROCS} /work/osu-container/libexec/osu-micro-benchmarks/mpi/${bench} ${OSU_ARGS[*]} \
    " | tee "${out_file}"
  done
fi

log "Done. Results saved in ${E4S_CL_WORKDIR}"
log "  - Host Baseline: ${E4S_CL_WORKDIR}/host_*.txt"
log "  - e4s-cl Run:    ${E4S_CL_WORKDIR}/e4scl_*.txt"
if [[ "${E4S_CL_RUN_CONTAINER_BASELINE}" == "1" ]]; then
log "  - Container Run: ${E4S_CL_WORKDIR}/container_*.txt"
fi

TIME_FILE="${E4S_CL_WORKDIR}/timing.dat"
python3 -c "
import sys
import os

def get_perf_val(filepath, bench_name):
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Filter data lines
        data_lines = [l.strip().split() for l in lines if l.strip() and l.strip()[0].isdigit()]
        if not data_lines: return 'N/A'

        if 'osu_bw' in bench_name:
            # Bandwidth: return the value from the largest size (last line)
            return data_lines[-1][1]
        else:
            # Latency (pt2pt or collective): return value for size 8
            for row in data_lines:
                if row[0] == '8':
                    return row[1]
            return 'N/A'
    except Exception:
        return 'N/A'

time_data = {}
try:
    if os.path.exists('${TIME_FILE}'):
        with open('${TIME_FILE}', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    time_data[parts[0]] = parts[1]
except Exception:
    pass

benches = '${OSU_BENCHES[*]}'.split()
workdir = '${E4S_CL_WORKDIR}'

print('\n[e4s-cl-test] --- Results Summary ---')
print(f'{\"Benchmark\":<20} {\"Metric (Size)\":<15} {\"Host\":<10} {\"E4S-CL\":<10} {\"Container\":<10}')

for b in benches:
    b_name = os.path.basename(b)
    
    # Timing
    h_time = time_data.get(f'host_{b_name}', 'N/A')
    e_time = time_data.get(f'e4scl_{b_name}', 'N/A')
    c_time = time_data.get(f'container_{b_name}', 'off')
    
    # Performance
    metric_label = 'Latency (8B)'
    if 'osu_bw' in b_name:
        metric_label = 'BW (Max)'
        
    h_perf = get_perf_val(os.path.join(workdir, f'host_{b_name}.txt'), b_name)
    e_perf = get_perf_val(os.path.join(workdir, f'e4scl_{b_name}.txt'), b_name)
    c_perf = 'off'
    if c_time != 'off':
        c_perf = get_perf_val(os.path.join(workdir, f'container_{b_name}.txt'), b_name)

    print(f'{b_name:<20} {\"Time (s)\":<15} {h_time:<10} {e_time:<10} {c_time:<10}')
    print(f'{\" \":<20} {metric_label:<15} {h_perf:<10} {e_perf:<10} {c_perf:<10}')
    print('-' * 70)
"
