# Releasing

Releases are cut by maintainers. Publishing runs in GitHub Actions only when a
GitHub release is published; nothing publishes on ordinary pushes.

## One-time setup

1. On PyPI, add a [trusted publisher](https://docs.pypi.org/trusted-publishers/)
   for project `typoprint`: owner `esandorfi`, repository `typoprint`, workflow
   `release.yml`, environment `pypi`. For a first upload use a *pending* publisher.
2. In the GitHub repository, create an environment named `pypi`. Optionally require
   a reviewer so each release needs approval.
3. In **Settings → Pages**, set the source to **GitHub Actions**.

No API tokens are stored in the repository.

## Cut a release

1. Update `version` in `pyproject.toml` and move the `CHANGELOG.md` entries from
   *Unreleased* under the new version and date.
2. Run the checks and build locally:

   ```bash
   uv sync --locked
   uv run ruff format --check .
   uv run ruff check .
   uv run ty check
   uv run pytest
   uv build
   ```

3. Merge to `main`, then tag and publish a GitHub release named `vX.Y.Z`
   (the tag must match `pyproject.toml`).
4. The release workflow rebuilds, verifies the clean wheel, publishes to PyPI, and
   attaches the files to the GitHub release. The documentation site redeploys from
   `main` on every docs change.

Check a published version with:

```bash
uv run --no-project --with typoprint==X.Y.Z typoprint --help
```
