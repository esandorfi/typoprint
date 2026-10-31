# Contributing to Typoprint

Thanks for helping. Typoprint is MIT licensed and welcomes issues and pull requests.

## Set up

Python 3.13+ and [uv](https://docs.astral.sh/uv/) are required.

```bash
git clone https://github.com/esandorfi/typoprint.git
cd typoprint
uv sync --locked
```

## Before opening a pull request

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

Tests use real temporary input files and the real Typst compiler. Update the user
documentation in `docs/` when behavior changes, and add an entry under
*Unreleased* in `CHANGELOG.md`. Preview the docs with
`uv sync --group docs && uv run mkdocs serve`.

## Design rules

- Keep the library and CLI thin and share one rendering pipeline.
- Rendering stays synchronous, offline with bundled resources, and isolated per
  invocation.
- Never rewrite source Markdown, execute embedded Typst from Markdown, or discover
  Python plugins from TOML.
- Keep dependency and font licenses beside bundled assets.

See [AGENTS.md](AGENTS.md) for the full contributor rules and
[docs/releasing.md](docs/releasing.md) for how releases are made.
