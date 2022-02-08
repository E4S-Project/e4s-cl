#!/usr/bin/env python3

import sys
import json
import e4s_cl
from e4s_cl import cli
from e4s_cl.cli import commands
from e4s_cl.cli.commands import __main__
from argparse import _StoreAction

command_tree = e4s_cl.cli._get_commands('e4s_cl.cli.commands')
command_tree['__module__'] = e4s_cl.cli.commands.__main__

ARGS_UNSPECIFIED = -1
PROFILE_MARKER = "__e4s_cl_profile"

ARG_TYPES = {'?': 'ARGS_ATMOSTONE', '+': 'ARGS_ATLEASTONE', '*': 'ARGS_SOME'}


class ParserNode:

    def __default__(self):
        for att, t in self.__class__.attributes.items():
            setattr(self, att, t())

    def __init__(self, **kwargs):
        self.__default__()
        for (x, y) in kwargs.items():
            setattr(self, x, y)

    def json(self):
        data = {}

        for field in self.__class__.attributes:
            if value := getattr(self, field, None):
                data[field] = value

        return data


class Positional(ParserNode):

    attributes = {'arguments': int, 'values': list, 'type': str}


class Option(ParserNode):

    attributes = {'names': list, 'arguments': int, 'values': list, 'type': str}


class Command(ParserNode):

    attributes = {
        'name': str,
        'subcommands': list,
        'positionals': list,
        'options': list,
    }

    def __init__(self, name, dict_):
        self.__default__()
        self.name = name

        command = dict_.pop('__module__').COMMAND

        if command.__class__ == 'RootCommand':
            print(f"{self.name} is a root command")

        for action in command.parser.actions:
            # Explicitly state that a StoreAction has an argument
            if isinstance(action, _StoreAction) and not action.nargs:
                action.nargs = 1

            # Translate character nargs to identifiers
            if action.nargs in ARG_TYPES:
                action.nargs = ARG_TYPES.get(action.nargs)

            # Used for subcommand matching; ignore it
            if action.nargs == '...':
                continue

            # If not option strings, this is a positional action
            if not action.option_strings:
                if not (action.nargs and action.type):
                    continue

                self.positionals.append(
                    Positional(arguments=action.nargs,
                               values=list(action.choices or []),
                               type=getattr(action.type, '__name__', None)))
                continue

            self.options.append(
                Option(names=action.option_strings,
                       arguments=action.nargs,
                       values=list(action.choices or []),
                       type=getattr(action.type, '__name__', None)))

        self.subcommands = [Command(*i) for i in dict_.items()]

    def json(self):
        data = {}

        for field in self.__class__.attributes:
            if value := getattr(self, field, None):
                data[field] = value

            if field in ['subcommands', 'options', 'positionals'
                         ] and (value := getattr(self, field, None)):
                data[field] = [k.json() for k in value]

        return data


if __name__ == "__main__":
    json.dump(Command('root', command_tree).json(),
              sys.stdout,
              separators=(',', ':'))
