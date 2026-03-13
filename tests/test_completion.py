"""Tests for e4s_cl.scripts.completion — static bash completion generator.

Coverage:
  CompletionGeneratorTest   tests generate_bash() and generate_completion_tree()
  CompletionInstallTest     tests regenerate_bash(), main(), _load_profile_names()
  CompletionFreshnessTest   tests that committed completions/e4s-cl.bash is current
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests
import e4s_cl.scripts.completion as comp


# ── Tiny synthetic CLI tree (no e4s_cl import needed for logic tests) ─────────
_SIMPLE_TREE = {
    'name': 'root',
    'subcommands': [
        {
            'name': 'launch',
            'options': [
                {'names': ['--profile', '-p'], 'arguments': 1,
                 'expected_type': 'defined_profile'},
                {'names': ['--image'], 'arguments': 1},
                {'names': ['--verbose'], 'arguments': 0},
            ],
        },
        {
            'name': 'profile',
            'subcommands': [
                {
                    'name': 'select',
                    'positionals': [
                        {'arguments': 1, 'expected_type': 'defined_profile'}
                    ],
                    'options': [{'names': ['--help', '-h'], 'arguments': 0}],
                },
                {
                    'name': 'list',
                    'options': [{'names': ['--help', '-h'], 'arguments': 0}],
                },
            ],
        },
        {'name': '__hidden', 'options': []},
    ],
    'options': [
        {'names': ['--debug'], 'arguments': 0},
        {'names': ['--from'], 'arguments': 1,
         'values': ['openmpi', 'mpich'], 'expected_type': ''},
    ],
}


class CompletionGeneratorTest(tests.TestCase):
    """Tests for the bash-script generator (no filesystem or e4s_cl import)."""

    def _bash(self, tree=None):
        return comp.generate_bash(tree or _SIMPLE_TREE)

    def test_generate_bash_returns_string(self):
        out = self._bash()
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 100)

    def test_generated_bash_syntax_valid(self):
        result = subprocess.run(
            ['bash', '-n'],
            input=self._bash().encode(),
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0,
                         f'bash -n failed:\n{result.stderr.decode()}')

    def test_generated_bash_has_complete_line(self):
        out = self._bash()
        self.assertIn('complete -F _e4s_cl_comp', out)
        self.assertIn('e4s-cl', out)

    def test_generated_bash_has_main_function(self):
        self.assertIn('_e4s_cl_comp() {', self._bash())

    def test_generated_bash_has_profile_helper(self):
        self.assertIn(comp._PROFILE_FN + '()', self._bash())

    def test_generated_bash_has_subcommands(self):
        out = self._bash()
        self.assertIn('launch', out)
        self.assertIn('profile', out)

    def test_generated_bash_hides_dunder_commands(self):
        out = self._bash()
        # __hidden must not appear in any compgen -W word-list
        for line in out.splitlines():
            if 'compgen' in line:
                self.assertNotIn('__hidden', line)

    def test_generated_bash_has_options(self):
        out = self._bash()
        self.assertIn('--debug', out)
        self.assertIn('--image', out)
        self.assertIn('--profile', out)

    def test_generated_bash_choices_inlined(self):
        # --from has choices ['openmpi', 'mpich'] — they must appear in the
        # generated case block for --from
        out = self._bash()
        self.assertIn('openmpi', out)
        self.assertIn('mpich', out)

    def test_generated_bash_profile_option_calls_helper(self):
        out = self._bash()
        # --profile and -p should trigger the profile-completion helper
        self.assertIn(comp._PROFILE_FN, out)

    def test_generate_completion_tree_returns_dict(self):
        tree = comp._generate_completion_tree()
        self.assertIsInstance(tree, dict)
        self.assertIn('subcommands', tree)

    def test_generate_completion_tree_has_launch(self):
        tree = comp._generate_completion_tree()
        names = [s['name'] for s in tree.get('subcommands', [])]
        self.assertIn('launch', names)

    def test_generate_completion_tree_has_profile_subcommands(self):
        tree = comp._generate_completion_tree()
        subs = {s['name']: s for s in tree.get('subcommands', [])}
        profile_subs = [s['name'] for s in subs.get('profile', {}).get('subcommands', [])]
        self.assertIn('list', profile_subs)
        self.assertIn('select', profile_subs)
        self.assertIn('create', profile_subs)

    def test_generate_completion_tree_idempotent(self):
        """Calling twice must not raise (tests shallow-copy fix for _COMMANDS)."""
        tree1 = comp._generate_completion_tree()
        tree2 = comp._generate_completion_tree()
        self.assertEqual(tree1, tree2)


class CompletionInstallTest(tests.TestCase):
    """Tests for regenerate_bash(), main(), and _load_profile_names()."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_bash_file = comp._BASH_FILE
        self._orig_db_path = comp._DB_PATH
        comp._BASH_FILE = Path(self._tmpdir) / 'completions' / 'e4s-cl.bash'
        comp._DB_PATH = Path(self._tmpdir) / 'user.json'

    def tearDown(self):
        comp._BASH_FILE = self._orig_bash_file
        comp._DB_PATH = self._orig_db_path
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    # ── regenerate_bash ────────────────────────────────────────────────────────

    def test_regenerate_creates_bash_file(self):
        comp.regenerate_bash()
        self.assertTrue(comp._BASH_FILE.exists())

    def test_regenerate_writes_valid_bash(self):
        comp.regenerate_bash()
        result = subprocess.run(
            ['bash', '-n', str(comp._BASH_FILE)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)

    def test_regenerate_idempotent(self):
        comp.regenerate_bash()
        content1 = comp._BASH_FILE.read_text()
        comp.regenerate_bash()
        content2 = comp._BASH_FILE.read_text()
        self.assertEqual(content1, content2)

    # ── main() ────────────────────────────────────────────────────────────────

    def test_main_regenerate_flag_creates_file(self):
        comp.main(['--regenerate'])
        self.assertTrue(comp._BASH_FILE.exists())

    def test_main_no_args_prints_source_when_file_exists(self):
        comp.regenerate_bash()
        out = io.StringIO()
        with patch('sys.stdout', out):
            comp.main([])
        self.assertIn('source', out.getvalue())
        self.assertIn('e4s-cl.bash', out.getvalue())

    def test_main_no_args_stderr_when_file_missing(self):
        err = io.StringIO()
        with patch('sys.stderr', err):
            comp.main([])
        self.assertIn('not found', err.getvalue().lower())

    # ── _load_profile_names ────────────────────────────────────────────────────

    def test_load_profile_names_empty_when_db_missing(self):
        names = comp._load_profile_names()
        self.assertEqual(names, [])

    def test_load_profile_names_reads_profiles(self):
        db_data = {'Profile': {'1': {'name': 'myprofile'}, '2': {'name': 'other'}}}
        comp._DB_PATH.write_text(json.dumps(db_data))
        names = comp._load_profile_names()
        self.assertIn('myprofile', names)
        self.assertIn('other', names)


class CompletionFreshnessTest(tests.TestCase):
    """Ensure the committed completions/e4s-cl.bash matches what the generator
    would produce today.  Fails loudly if a developer changes the CLI without
    regenerating the completion script.

    This test mirrors the CI workflow in .github/workflows/completion.yml.
    """

    def test_committed_bash_is_up_to_date(self):
        repo_file = Path(__file__).parent.parent / 'completions' / 'e4s-cl.bash'
        if not repo_file.exists():
            self.skipTest('completions/e4s-cl.bash not present in repo')
        tree = comp._generate_completion_tree()
        current = comp.generate_bash(tree)
        committed = repo_file.read_text()
        self.assertEqual(
            current, committed,
            'completions/e4s-cl.bash is out of date.\n'
            'Regenerate it with:\n'
            '   python scripts/generate_completion_bash.py > completions/e4s-cl.bash\n'
            'and commit the result.',
        )
