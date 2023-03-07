import sys
from e4s_cl.cli.commands.__main__ import COMMAND as cli_main_cmd


def main():
    sys.exit(cli_main_cmd.main(sys.argv[1:]))
