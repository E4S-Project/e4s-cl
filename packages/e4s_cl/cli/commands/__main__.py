# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, ParaTools, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# (1) Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
# (2) Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
# (3) Neither the name of ParaTools, Inc. nor the names of its contributors may
#     be used to endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""TAU Commander command line program entry point.

Sets up logging verbosity and launches subcommands.  Avoid doing too much work here.
Instead, process arguments in the appropriate subcommand.
"""

import os
import sys
import e4s_cl
from e4s_cl import cli, logger, util, TAUCMDR_VERSION, E4S_CL_SCRIPT
from e4s_cl.cli import UnknownCommandError, arguments
from e4s_cl.cli.command import AbstractCommand

LOGGER = logger.get_logger(__name__)

HELP_PAGE_FMT = """'%(command)s' page to be written."""

class MainCommand(AbstractCommand):
    """Main entry point to the command line interface."""

    def __init__(self):
        summary_parts = [util.color_text("TAU Commander %s" % TAUCMDR_VERSION, 'red', attrs=['bold']),
                         util.color_text(" [ ", attrs=['bold']),
                         util.color_text(e4s_cl.TAUCMDR_URL, 'cyan', attrs=['bold']),
                         util.color_text(" ]", attrs=['bold'])] 
        super(MainCommand, self).__init__(__name__, summary_fmt=''.join(summary_parts), help_page_fmt=HELP_PAGE_FMT)
        self.command = os.path.basename(E4S_CL_SCRIPT)
    
    def _construct_parser(self):
        usage = "%s [arguments] <subcommand> [options]"  % self.command
        _green = lambda x: "{:<35}".format(util.color_text(x, 'green'))
        epilog_parts = ["", cli.commands_description(), "",
                        "See `%(command)s help <subcommand>` for more information on a subcommand."]
        epilog = '\n'.join(epilog_parts) % {'color_command': util.color_text(self.command, 'cyan'), 
                                            'command': self.command}
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary,
                                      epilog=epilog)
        parser.add_argument('command',
                            help="See subcommand descriptions below",
                            metavar='<subcommand>')
        parser.add_argument('options',
                            help="Options to be passed to <subcommand>",
                            metavar='[options]',
                            nargs=arguments.REMAINDER)
        parser.add_argument('-V', '--version', action='version', version=e4s_cl.version_banner())
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-v', '--verbose',
                           help="show debugging messages",
                           const='DEBUG',
                           default=arguments.SUPPRESS,
                           action='store_const')
        group.add_argument('-q', '--quiet',
                           help="suppress all output except error messages",
                           const='ERROR',
                           default=arguments.SUPPRESS,
                           action='store_const')        
        return parser
            
    def main(self, argv):
        """Program entry point.

        Args:
            argv (list): Command line arguments.

        Returns:
            int: Process return code: non-zero if a problem occurred, 0 otherwise
        """
        args = self._parse_args(argv)
        cmd = args.command
        cmd_args = args.options
        
        log_level = getattr(args, 'verbose', getattr(args, 'quiet', logger.LOG_LEVEL))
        logger.set_log_level(log_level)
        LOGGER.debug('Arguments: %s', args)
        LOGGER.debug('Verbosity level: %s', logger.LOG_LEVEL)

        # Try to execute as a TAU command
        try:
            return cli.execute_command([cmd], cmd_args)
        except UnknownCommandError:
            pass

        # Not sure what to do at this point, so advise the user and exit
        LOGGER.info("Unknown command.  Calling `%s help %s` to get advice.", E4S_CL_SCRIPT, cmd)
        return cli.execute_command(['help'], [cmd])

COMMAND = MainCommand()

if __name__ == '__main__':
    sys.exit(COMMAND.main(sys.argv[1:]))
