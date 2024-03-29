"""mpirun launcher support"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['mpirun']

_global = {
    "--allow-run-as-root": 0,
    "--app": 1,
    "--bind-to": 1,
    "--continuous": 0,
    "--daemonize": 0,
    "--debug": 0,
    "--debug-daemons": 0,
    "--debug-daemons-file": 0,
    "--debug-devel": 0,
    "--debug-verbose": 1,
    "--default-hostfile": 1,
    "--disable-recovery": 0,
    "--display-allocation": 0,
    "--display-devel-allocation": 0,
    "--display-devel-map": 0,
    "--display-diffable-map": 0,
    "--display-map": 0,
    "--display-topo": 0,
    "--do-not-launch": 0,
    "--do-not-resolve": 0,
    "--enable-recovery": 0,
    "--forward-signals": 1,
    "--fwd-mpirun-port": 0,
    "--get-stack-traces": 0,
    "--gomca": 2,
    "--gpmixmca": 2,
    "--help": 0,
    "--host": 1,
    "--hostfile": 1,
    "--index-argv-by-rank": 0,
    "--launch-agent": 1,
    "--leave-session-attached": 0,
    "--machinefile": 1,
    "--map-by": 1,
    "--max-restarts": 1,
    "--max-vm-size": 1,
    "--mca": 2,
    "--merge-stderr-to-stdout": 0,
    "--n": 1,
    "--no-ready-msg": 0,
    "--noprefix": 0,
    "--np": 1,
    "--omca": 2,
    "--ompi-server": 1,
    "--output-directory": 1,
    "--output-filename": 1,
    "--output-proctable": 1,
    "--oversubscribe": 0,
    "--parsable": 0,
    "--parseable": 0,
    "--path": 1,
    "--personality": 1,
    "--pmixam": 1,
    "--pmixmca": 2,
    "--prefix": 1,
    "--preload-binary": 0,
    "--preload-files": 1,
    "--prte_info_pretty": 0,
    "--prtemca": 2,
    "--pset": 1,
    "--quiet": 0,
    "--rank-by": 1,
    "--report-bindings": 0,
    "--report-child-jobs-separately": 0,
    "--report-pid": 1,
    "--report-state-on-timeout": 0,
    "--report-uri": 1,
    "--set-cwd-to-session-dir": 0,
    "--set-sid": 0,
    "--show-progress": 0,
    "--stdin": 1,
    "--stop-on-exec": 0,
    "--stream-buffering": 1,
    "--system-server": 0,
    "--tag-output": 0,
    "--test-suicide": 1,
    "--timeout": 1,
    "--timestamp-output": 0,
    "--tmpdir": 1,
    "--tune": 1,
    "--verbose": 0,
    "--version": 0,
    "--wd": 1,
    "--wdir": 1,
    "--xml": 0,
    "--xterm": 1,
    "-H": 1,
    "-N": 1,
    "-V": 0,
    "-c": 1,
    "-configfile": 1,
    "-d": 0,
    "-env": 2,
    "-envall": 0,
    "-envlist": 1,
    "-envnone": 0,
    "-f": 1,
    "-genv": 2,
    "-genvall": 0,
    "-genvlist": 1,
    "-genvnone": 0,
    "-h": 0,
    "-hosts": 1,
    "-n": 1,
    "-np": 1,
    "-q": 0,
    "-s": 0,
    "-v": 0,
    "-wdir": 1,
    "-x": 1,
}

_intel_options = {
    '-aps': 0,
    '-gtool': 0,
    '-gtoolfile': 1,
    '-hosts-group': 1,
    '-mps': 0,
}

_hydra_options = {
    "-bind-to": 1,
    "-disable-auto-cleanup": 0,
    "-disable-hostname-propagation": 0,
    "-disable-x": 0,
    "-enable-x": 0,
    "-errfile-pattern": 0,
    "-iface": 1,
    "-info": 0,
    "-launcher": 1,
    "-launcher-exec": 1,
    "-localhost": 0,
    "-map-by": 1,
    "-membind": 1,
    "-nameserver": 0,
    "-nolocal": 0,
    "-outfile-pattern": 0,
    "-ppn": 1,
    "-prepend-pattern": 0,
    "-prepend-rank": 0,
    "-print-all-exitcodes": 0,
    "-print-rank-map": 0,
    "-rmk": 1,
    "-s": 1,
    "-silent-abort": 0,
    "-tune": 1,
    "-usize": 0,
    "-verbose": 0,
}

_wi4mpi_options = {
    "-E": 1,
    "-extra": 1,
    "--extra": 1,
    "-F": 1,
    "-from": 1,
    "--from": 1,
    "-T": 1,
    "-to": 1,
    "--to": 1,
    "-p": 1,
    "-pm": 1,
    "--pm": 1,
    "-h": 0,
    "-help": 0,
    "--help": 0,
    "-V": 0,
    "-version": 0,
    "--version": 0,
}

_wi4mpi_passed = {
    "-f": 1,
    "-hostfile": 1,
    "--hostfile": 1,
    "-n": 1,
    "-np": 1,
    "-v": 0,
    "-verbose": 0,
    "--verbose": 0,
}

PARSER = Parser({
    **_global,
    **_intel_options,
    **_hydra_options,
    **_wi4mpi_options
})
# Uncomment when py39 comes around
# PARSER = Parser(_global | _intel_options | _hydra_options)
