#!/usr/bin/env python3
"""Thin wrapper: generate the static bash completion script for e4s-cl.

Run::

    python scripts/generate_completion_bash.py > completions/e4s-cl.bash
    # or just let main() write the file in-place:
    python scripts/generate_completion_bash.py --in-place

Requires e4s_cl to be importable (``pip install -e .`` or equivalent).
The generated file is committed to the repository and its freshness is
verified in CI.

All generation logic lives in ``e4s_cl/scripts/completion.py``; this script
is just a convenient CLI wrapper.
"""
import sys
from pathlib import Path

# Allow running directly from repo root without a prior install.
sys.path.insert(0, str(Path(__file__).parent.parent))

from e4s_cl.scripts.completion import (  # noqa: E402
    _generate_completion_tree,
    generate_bash,
    regenerate_bash,
)

if __name__ == '__main__':
    if '--in-place' in sys.argv:
        regenerate_bash()
    else:
        print(generate_bash(_generate_completion_tree()), end='')
