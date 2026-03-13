#!/usr/bin/env python3
"""Shell completion support for e4s-cl.

Generates a static bash ``complete -F`` completion script from the live
e4s_cl CLI parsers.  The generated script is committed to the repository as
``completions/e4s-cl.bash`` and its freshness is verified in CI.

Runtime design
--------------
* All subcommand names and option flags are **inlined as string literals** in
  the generated bash function → zero subprocess cost for the common case.
* Dynamic profile names are fetched via an embedded ``python3`` heredoc in
  the bash function → subprocess only for profile-name argument slots.

Entry point (``main()``)
------------------------
* No arguments → print the ``source /path`` setup snippet.
* ``--regenerate`` → rebuild ``completions/e4s-cl.bash`` from live parsers.

For users
---------
* ``make install``: Makefile copies ``completions/e4s-cl.bash`` to
  ``COMPLETION_DIR`` (auto-sourced by bash-completion on new shells).
* Git clone / editable install: ``source /repo/completions/e4s-cl.bash``.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

# ── Profile store path ────────────────────────────────────────────────────────
# Honour the same env-var override used by e4s_cl storage so tests that set
# __E4S_CL_USER_PREFIX__ to a temp dir work correctly.
_DB_PATH = (
    Path(os.environ.get('__E4S_CL_USER_PREFIX__',
                        Path.home() / '.local' / 'e4s_cl'))
    / 'user.json'
)

# Location of the canonical generated bash completion file.
# Path: e4s_cl/scripts/completion.py → ../../completions/e4s-cl.bash
_BASH_FILE = Path(__file__).parent.parent.parent / 'completions' / 'e4s-cl.bash'

# ── ArgumentCount / ExpectedType constants ────────────────────────────────────
_AC_ATMOSTONE  = 'ARGS_ATMOSTONE'
_AC_ATLEASTONE = 'ARGS_ATLEASTONE'
_AC_SOME       = 'ARGS_SOME'
_ET_PROFILE    = 'defined_profile'

_PROFILE_FN = '__e4s_cl_complete_profiles'

# ── Profile loader — no e4s_cl import ────────────────────────────────────────

def _load_profile_names() -> list[str]:
    """Read profile names directly from the tinydb JSON (no e4s_cl import)."""
    try:
        with open(_DB_PATH) as fh:
            data = json.load(fh)
        return [
            v['name']
            for v in data.get('Profile', {}).values()
            if isinstance(v, dict) and 'name' in v
        ]
    except Exception:
        return []


# ── Bash generation helpers ───────────────────────────────────────────────────

def _nargs_takes_arg(nargs) -> bool:
    """Return True if this nargs value means the option consumes ≥1 argument."""
    if nargs is None or nargs == 0:
        return False
    if isinstance(nargs, int) and nargs > 0:
        return True
    return nargs in (_AC_ATMOSTONE, _AC_ATLEASTONE, _AC_SOME)


def _all_option_names(command: dict) -> list[str]:
    return [name for opt in command.get('options', [])
            for name in opt.get('names', [])]


def _profile_option_patterns(command: dict) -> list[str]:
    """Return option flags whose argument expects a profile name."""
    names: list[str] = []
    for opt in command.get('options', []):
        if (opt.get('expected_type') == _ET_PROFILE
                and _nargs_takes_arg(opt.get('arguments'))):
            names.extend(opt.get('names', []))
    return names


def _choices_options(command: dict) -> dict[str, list[str]]:
    """Return ``{flag: [choice, …]}`` for options with a fixed choices list."""
    result: dict[str, list[str]] = {}
    for opt in command.get('options', []):
        if opt.get('expected_type') == _ET_PROFILE:
            continue
        if opt.get('values') and _nargs_takes_arg(opt.get('arguments')):
            for name in opt.get('names', []):
                result[name] = opt['values']
    return result


def _positional_profile_indices(command: dict) -> list[int]:
    """Return 0-based indices of positionals with ``defined_profile`` type."""
    return [
        i for i, p in enumerate(command.get('positionals', []))
        if p.get('expected_type') == _ET_PROFILE
    ]


def _subcommand_names(command: dict) -> list[str]:
    """Return subcommand names, excluding internal ``__*`` commands."""
    return [
        s['name'] for s in command.get('subcommands', [])
        if not s['name'].startswith('__')
    ]


def _indent(lines: list[str], n: int) -> list[str]:
    pad = '    ' * n
    return [pad + line if line else '' for line in lines]


def _emit_option_arg_block(command: dict, indent_level: int) -> list[str]:
    """Emit a ``case "$prev" in`` block handling option-with-argument slots."""
    profile_pats = _profile_option_patterns(command)
    choices_map = _choices_options(command)

    if not profile_pats and not choices_map:
        return []

    lines: list[str] = ['case "$prev" in']
    if profile_pats:
        pat = '|'.join(profile_pats)
        lines += [
            f'    {pat})',
            f'        {_PROFILE_FN} "$cur"; return ;;',
        ]
    for flag, choices in choices_map.items():
        cw = ' '.join(choices)
        lines += [
            f'    {flag})',
            f'        COMPREPLY=($(compgen -W {repr(cw)} -- "$cur")); return ;;',
        ]
    lines += ['esac']
    return _indent(lines, indent_level)


def _emit_command_body(command: dict, word_index: int,
                       indent_level: int) -> list[str]:
    """Recursively emit the completion body for one command node.

    ``word_index`` is the index into ``$words`` that selects this command
    (1 for root, 2 for first-level subcommands, …).
    """
    lines: list[str] = []
    pad = '    ' * indent_level

    # Option-argument check: $prev is an option that consumes a value.
    lines += _emit_option_arg_block(command, indent_level)

    subs = command.get('subcommands', [])
    opts = _all_option_names(command)
    pos_profile_idx = _positional_profile_indices(command)

    if subs:
        sub_names = _subcommand_names(command)
        visible_subs = [s for s in subs if not s['name'].startswith('__')]
        lines += [f'{pad}case "${{words[{word_index}]}}" in']
        for sub in visible_subs:
            lines += [f'{pad}    {sub["name"]})']
            sub_body = _emit_command_body(sub, word_index + 1, indent_level + 2)
            lines += sub_body
            lines += [f'{pad}        ;;']
        # Default: offer subcommand names and any options at this level.
        word_list = ' '.join(sub_names + opts)
        lines += [
            f'{pad}    *)',
            f'{pad}        COMPREPLY=($(compgen -W {repr(word_list)} -- "$cur"))',
            f'{pad}        ;;',
            f'{pad}esac',
        ]
    else:
        # Leaf command: offer profile positional or option flags.
        if pos_profile_idx:
            lines += [
                f'{pad}# Complete a positional profile name.',
                f'{pad}if [[ $cword -ge {word_index} && "$cur" != -* ]]; then',
                f'{pad}    {_PROFILE_FN} "$cur"; return',
                f'{pad}fi',
            ]
        if opts:
            word_list = ' '.join(opts)
            lines += [
                f'{pad}COMPREPLY=($(compgen -W {repr(word_list)} -- "$cur"))',
            ]

    return lines


def generate_bash(tree: dict) -> str:
    """Return the full static bash completion script for e4s-cl as a string."""

    # Profile-completion helper: embedded python3 script reads the tinydb
    # profile store directly — no dependency on any installed binary.
    profile_fn = textwrap.dedent(f"""\
        {_PROFILE_FN}() {{
            local _profiles
            _profiles=$(python3 - <<'_PY_EOF' 2>/dev/null
        import json, os, pathlib
        _db = (
            pathlib.Path(os.environ.get('__E4S_CL_USER_PREFIX__',
                         str(pathlib.Path.home() / '.local' / 'e4s_cl')))
            / 'user.json'
        )
        try:
            _d = json.loads(open(_db).read())
            print(' '.join(
                v['name']
                for v in _d.get('Profile', {{}}).values()
                if isinstance(v, dict) and 'name' in v
            ))
        except Exception:
            pass
        _PY_EOF
        )
            COMPREPLY=($(compgen -W "$_profiles" -- "$1"))
        }}""")

    root_body = _emit_command_body(tree, word_index=1, indent_level=1)

    main_fn = '\n'.join([
        '_e4s_cl_comp() {',
        '    local cur prev words cword',
        '    # Use bash-completion helper if available; fall back to raw COMP_WORDS.',
        '    _init_completion 2>/dev/null || {',
        '        words=("${COMP_WORDS[@]}")',
        '        cword=$COMP_CWORD',
        '        cur="${COMP_WORDS[$COMP_CWORD]}"',
        '        prev="${COMP_WORDS[$((COMP_CWORD-1))]}"',
        '    }',
        '',
    ] + root_body + ['}'])

    header = textwrap.dedent("""\
        # Bash completion for e4s-cl
        # Auto-generated by scripts/generate_completion_bash.py — do not edit manually.
        # To regenerate: python scripts/generate_completion_bash.py > completions/e4s-cl.bash
        #
        # Installation (pick one):
        #   make install                               — copies to bash-completion user dir
        #   source /path/to/e4s-cl/completions/e4s-cl.bash  — one-time manual setup
        """)

    footer = '\ncomplete -F _e4s_cl_comp -o bashdefault -o default e4s-cl\n'

    return header + '\n' + profile_fn + '\n\n' + main_fn + footer


# ── Completion tree generator — imports e4s_cl ────────────────────────────────

def _generate_completion_tree() -> dict:
    """Build the completion tree by introspecting the live CLI parsers.

    Imports the full ``e4s_cl`` package — call only at build / regeneration
    time, never from a latency-sensitive path.
    """
    from argparse import _StoreAction
    from e4s_cl import cli
    from e4s_cl.cli.commands import __main__ as main_mod  # noqa: F401

    _ARG_TYPES: dict[str, str] = {
        '?': 'ARGS_ATMOSTONE',
        '+': 'ARGS_ATLEASTONE',
        '*': 'ARGS_SOME',
    }

    command_tree = cli._get_commands('e4s_cl.cli.commands')
    command_tree['__module__'] = main_mod

    class _Positional:
        def __init__(self, **kw):
            self.arguments: int | str = 0
            self.values: list[str] = []
            self.expected_type: str = ''
            for k, v in kw.items():
                setattr(self, k, v)

        def json(self) -> dict:
            d: dict = {}
            if self.arguments:
                d['arguments'] = self.arguments
            if self.values:
                d['values'] = self.values
            if self.expected_type:
                d['expected_type'] = self.expected_type
            return d

    class _Option:
        def __init__(self, **kw):
            self.names: list[str] = []
            self.arguments: int | str = 0
            self.values: list[str] = []
            self.expected_type: str = ''
            for k, v in kw.items():
                setattr(self, k, v)

        def json(self) -> dict:
            d: dict = {}
            if self.names:
                d['names'] = self.names
            if self.arguments:
                d['arguments'] = self.arguments
            if self.values:
                d['values'] = self.values
            if self.expected_type:
                d['expected_type'] = self.expected_type
            return d

    class _Command:
        def __init__(self, name: str, dict_: dict):
            self.name = name
            self.subcommands: list = []
            self.positionals: list = []
            self.options: list = []

            # Shallow-copy so dict_.pop('__module__') does not mutate the
            # live e4s_cl.cli._COMMANDS global — which would cause a KeyError
            # on the second call to _generate_completion_tree().
            dict_ = dict(dict_)
            mod = dict_.pop('__module__')
            command = mod.COMMAND

            for action in command.parser.actions:
                nargs = action.nargs
                if isinstance(action, _StoreAction) and not nargs:
                    nargs = 1

                if nargs in _ARG_TYPES:
                    nargs = _ARG_TYPES[nargs]

                if nargs == '...':
                    continue

                if not action.option_strings:
                    if not (nargs and action.type):
                        continue
                    self.positionals.append(_Positional(
                        arguments=nargs,
                        values=sorted(action.choices or []),
                        expected_type=getattr(action.type, '__name__', '') or '',
                    ))
                    continue

                self.options.append(_Option(
                    names=action.option_strings,
                    arguments=nargs,
                    values=sorted(action.choices or []),
                    expected_type=getattr(action.type, '__name__', '') or '',
                ))

            self.subcommands = [_Command(*item) for item in dict_.items()]

        def json(self) -> dict:
            d: dict = {'name': self.name}
            if self.subcommands:
                d['subcommands'] = [c.json() for c in self.subcommands]
            if self.positionals:
                d['positionals'] = [p.json() for p in self.positionals]
            if self.options:
                d['options'] = [o.json() for o in self.options]
            return d

    return _Command('root', command_tree).json()


# ── Public API ────────────────────────────────────────────────────────────────

def regenerate_bash(dest: Path | None = None) -> None:
    """Rebuild the bash completion script from the live CLI parsers.

    Writes to *dest* (defaults to :data:`_BASH_FILE`).  Silently ignores any
    exception so callers are never disrupted.
    """
    target = dest or _BASH_FILE
    try:
        tree = _generate_completion_tree()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(generate_bash(tree))
    except Exception:  # pragma: no cover
        pass


# ── Developer utilities ──────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    """Convenience entry point for regenerating the bash completion script.

    * No arguments → print the path to source for manual setup.
    * ``--regenerate`` → rebuild :data:`_BASH_FILE` from live parsers.

    Users and CI should prefer running the generator directly::

        python scripts/generate_completion_bash.py > completions/e4s-cl.bash
    """
    if argv is None:
        argv = sys.argv[1:]

    if '--regenerate' in argv:
        regenerate_bash()
        return

    if _BASH_FILE.exists():
        print(f'source {_BASH_FILE.resolve()}')
    else:
        print(
            '# e4s-cl completion script not found.\n'
            '# Run  make install  or manually:\n'
            '#   source /path/to/e4s-cl/completions/e4s-cl.bash',
            file=sys.stderr,
        )


if __name__ == '__main__':
    main()

