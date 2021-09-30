#!/usr/bin/env python3

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


class Option:
    def __default__(self):
        self.names = []
        self.arguments = 0
        self.values = []

    def __init__(self, **kwargs):
        self.__default__()
        for (x, y) in kwargs.items():
            setattr(self, x, y)

    def json(self):
        data = {}

        fields = ['names', 'arguments', 'values']

        for field in fields:
            if value := getattr(self, field, None):
                data[field] = value

        return data


class Command:
    def __default__(self):
        self.name = ""
        self.subcommands = []
        self.options = []
        self.arguments = 0
        self.values = []

    def __init__(self, name, dict_):
        self.__default__()
        self.name = name

        command = dict_.pop('__module__').COMMAND

        for action in command.parser.actions:
            if not action.option_strings:
                if action.dest == 'profile':
                    self.values = [PROFILE_MARKER]
                    self.arguments = 1
                continue

            if action.option_strings == ['--profile']:
                action.choices = [PROFILE_MARKER]

            if isinstance(action, _StoreAction):
                action.nargs = 1

            if action.nargs in ['*', '+']:
                action.nargs = ARGS_UNSPECIFIED

            self.options.append(
                Option(names=action.option_strings,
                       arguments=(action.nargs or 0),
                       values=(action.choices or [])))

        self.subcommands = [Command(*i) for i in dict_.items()]

    def json(self):
        data = {}

        fields = ['name', 'subcommands', 'options', 'arguments', 'values']

        for field in fields:
            if value := getattr(self, field, None):
                data[field] = value

            if field in ['subcommands', 'options'] and (value := getattr(
                    self, field, None)):
                data[field] = [k.json() for k in value]

        return data


if __name__ == "__main__":
    print(
        json.dumps(Command('root', command_tree).json(),
                   separators=(',', ':')))
