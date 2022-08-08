"""SLURM support, from srun 20.02.1"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['srun']

ARGUMENTS = {
    # Parallel options
    "-A": 1,  # Account name
    "-b": 1,  # Deferral (begin)
    "-c": 1,  # Cpus/task
    "--compress": 0,
    "-d": 1,
    "-e": 1,
    "-E": 0,
    "-H": 0,
    "-i": 1,
    "-I": 0,
    "--imediate": 0,
    "-J": 1,
    "-k": 0,
    "-K": 0,
    "-l": 0,
    "-L": 1,
    "-m": 1,
    "-M": 1,
    "--multi-prog": 0,
    "-n": 1,
    "-N": 1,
    "--nice": 0,
    "-o": 1,
    "-O": 0,
    "--overcommit": 0,
    "-p": 1,
    "--propagate": 0,
    "--pty": 0,
    "-q": 1,
    "-Q": 0,
    "--quiet": 0,
    "--quit-on-interrupt": 0,
    "-r": 1,
    "--reboot": 0,
    "-s": 0,
    "-S": 1,
    "--spread-job": 0,
    "-t": 1,
    "-T": 1,
    "-u": 0,
    "--unbuffered": 0,
    "--use-min-nodes": 0,
    "-v": 0,
    "--verbose": 0,
    "-W": 1,
    "-X": 0,
    "--disable-status": 0,
    # Constraint options
    "--contiguous": 0,
    "-C": 1,
    "-w": 1,
    "-x": 1,
    "-Z": 0,
    "--no-allocate": 0,
    # Resources
    "--exclusive": 0,
    "--resv-ports": 0,
    # Affinity
    "-B": 1,
    # GPUs
    "-G": 1,
    # Other
    "-h": 0,
    "--help": 0,
    "--usage": 0,
    "-V": 0,
    "--version": 0,
}

META = dict(reserved_directories=['/var/spool/slurm', '/var/spool/slurmd'])

PARSER = Parser(ARGUMENTS)
