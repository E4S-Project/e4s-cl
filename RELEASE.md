# Release Process

## Prerequisites

- Python 3 with `build` and `twine` installed.
- Push access to the repository and (optionally) PyPI.

## Prepare

1. Pull the latest changes.

        git pull --rebase

2. Update the version in `docs/conf.py`.

3. Update `CHANGELOG`.

4. If CLI commands or options changed, regenerate `completions/e4s-cl.bash`:

        python3 scripts/generate_completion_bash.py > completions/e4s-cl.bash

   The CI workflow (`.github/workflows/completion.yml`) will catch this if forgotten.

5. Run tests.

        tox --parallel auto

6. Commit.

        git commit -a -m "prepare release VERSION"

7. Push and verify CI passes.

        git push

## Tag and publish

1. Tag the release.

        git tag VERSION

2. Build distribution artifacts.

        python3 -m build

3. Push the tag.

        git push --tags

4. Upload to PyPI (optional).

        twine upload dist/*

## Post-release

1. Increment the version in `docs/conf.py`.

2. Commit and push.

        git commit -a -m "post-release"
        git push
