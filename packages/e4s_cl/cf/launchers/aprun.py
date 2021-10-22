"""ALPS launcher support, from aprun 6.6.59"""

from e4s_cl.cf.launchers import Parser

SCRIPT_NAMES = ['aprun']

ARGUMENTS = {
    ":": 0,
    "-a": 1,  #arch
    "--access-mode": 1,  #flag
    "--architecture": 1,  #arch
    "-b": 0,
    "-B": 0,
    "--batch-args": 0,
    "--bypass-app-transfer": 0,
    "-C": 0,
    "--cc": 1,  #cpu_list
    "--cp": 1,  #file
    "--cpu-binding": 1,  #cpu_list
    "--cpu-binding-file": 1,  #file
    "--cpus-per-cu": 1,  #CPUs
    "--cpus-per-pe": 1,  #depth
    "--cpu-time-limit": 1,  #sec
    "-D": 0,
    "-d": 1,  #depth
    "--debug level": 0,
    "-e": 1,  #env
    "-E": 1,  #node_list
    "--environment-override": 1,  #env
    "--exclude-node-list": 1,  #node_list
    "--exclude-node-list-file": 1,  #node_list_file
    "-F": 1,  #flag
    "--help": 0,
    "-j": 1,  #CPUs
    "-L": 1,  #node_list
    "-l": 1,  #node_list_file
    "-m": 1,  #size
    "--memory-per-pe": 1,  #size
    "--mpmd-env": 1,  #env
    "-N": 1,  #pes
    "-n": 1,  #width
    "--node-list": 1,  #node_list
    "--node-list-file": 1,  #node_list_file
    "-P": 0,
    "-p": 1,  #pdi
    "--pes": 1,  #width
    "--pes-per-node": 1,  #pes
    "--pes-per-numa-node": 1,  #pes
    "--p-governor": 1,  #governor_name
    "--pipes pipes": 0,
    "--protection-domain": 1,  #pdi
    "--p-state": 1,  #pstate
    "-q": 0,
    "--quiet": 0,
    "-r": 1,  #CPUs
    "-R": 1,  #max_shrink
    "--reconnect": 0,
    "--relaunch": 1,  #max_shrink
    "-S": 1,  #pes
    "--specialized-cpus": 1,  #CPUs
    "--ss": 0,
    "--strict-memory-containment": 0,
    "--sync-output": 0,
    "-T": 0,
    "-t": 1,  #sec
    "--version": 0,
    "--wdir": 1,  #wdir
    "-z": 0,
    "-Z": 1,  #secs
    "--zone-sort": 0,
    "--zone-sort-secs": 1,  #secs
}

PARSER = Parser(ARGUMENTS)
