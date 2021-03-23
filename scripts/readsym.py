#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Get a list of defined symbols in a ELF file, based on the pyelftools library
#
# Original code by
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

import argparse
import os, sys, json
import string
import traceback

from elftools import __version__
from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection
from elftools.elf.gnuversions import (
    GNUVerSymSection,
    GNUVerDefSection,
    GNUVerNeedSection,
)


class ReadElf(object):
    """ display_* methods are used to emit output into the output stream
    """
    def __init__(self, file):
        """ file:
                stream object with the ELF file to read

            output:
                output stream to write to
        """
        self.elffile = ELFFile(file)

        self._versioninfo = None

    def display_version_info(self):
        """ Display the version info contained in the file
        """
        self._query_sections()

        verdata = {'symbols': {}}

        if not self._versioninfo['type']:
            self._emitline("\nNo version information found in this file.")
            return verdata

        if self._versioninfo['dynamic']:
            needed_ = filter(lambda x: x.entry.d_tag == 'DT_NEEDED',
                             self._versioninfo['dynamic'].iter_tags())

            verdata['dependencies'] = [tag.needed for tag in needed_]

        if self._versioninfo['verdef']:
            verdefined = [
                next(verdaux_iter).name for verdef, verdaux_iter in
                self._versioninfo['verdef'].iter_versions()
            ]

            verdata['symbols']['defined'] = verdefined

        if self._versioninfo['verneed']:
            verneeded = {}

            for verneed, verneed_iter in self._versioninfo[
                    'verneed'].iter_versions():
                verneeded[verneed.name] = [
                    vernaux.name
                    for idx, vernaux in enumerate(verneed_iter, start=1)
                ]
            verdata['symbols']['needed'] = verneeded

        return verdata

    def _query_sections(self):
        """ Search and initialize informations about version related sections
            and the kind of versioning used (GNU or Solaris).
        """
        if self._versioninfo is not None:
            return

        self._versioninfo = {
            'versym': None,
            'verdef': None,
            'verneed': None,
            'dynamic': None,
            'type': None
        }

        for section in self.elffile.iter_sections():
            if isinstance(section, GNUVerSymSection):
                self._versioninfo['versym'] = section
            elif isinstance(section, GNUVerDefSection):
                self._versioninfo['verdef'] = section
            elif isinstance(section, GNUVerNeedSection):
                self._versioninfo['verneed'] = section
            elif isinstance(section, DynamicSection):
                self._versioninfo['dynamic'] = section
                for tag in section.iter_tags():
                    if tag['d_tag'] == 'DT_VERSYM':
                        self._versioninfo['type'] = 'GNU'
                        break

        if not self._versioninfo['type'] and (self._versioninfo['verneed']
                                              or self._versioninfo['verdef']):
            self._versioninfo['type'] = 'Solaris'


SCRIPT_DESCRIPTION = 'Display information about the symbols of ELF files'
VERSION_STRING = '%%(prog)s: based on pyelftools %s' % __version__


def main(stream=None):
    # parse the command-line arguments and invoke ReadElf
    argparser = argparse.ArgumentParser(
        usage='usage: %(prog)s <elf-file>',
        description=SCRIPT_DESCRIPTION,
        add_help=False,  # -h is a real option of readelf
        prog='readelf.py')
    argparser.add_argument('file',
                           nargs='?',
                           default=None,
                           help='ELF file to parse')
    argparser.add_argument('-H',
                           '--help',
                           action='store_true',
                           dest='help',
                           help='Display this information')

    args = argparser.parse_args()

    if args.help or not args.file:
        argparser.print_help()
        sys.exit(0)

    with open(args.file, 'rb') as file:
        try:
            readelf = ReadElf(file)
            print(json.dumps(readelf.display_version_info()))
        except ELFError as ex:
            sys.stdout.flush()
            sys.stderr.write('ELF error: %s\n' % ex)
            if args.show_traceback:
                traceback.print_exc()
            sys.exit(1)


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
