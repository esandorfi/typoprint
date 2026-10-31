# Install

Typoprint needs Python **3.13 or newer**. Rendering resources, Mermaid support,
and fonts ship with the package, so nothing else is required and no network is
used while rendering. Windows, Linux with glibc, and macOS are tested; Alpine
(musl) is not.

## From PyPI

Install the command-line tool in its own environment:

```bash
uv tool install typoprint
# or
pipx install typoprint
```

Add it to a Python project:

```bash
uv add typoprint
# or
pip install typoprint
```

Check the installation:

```bash
typoprint --help
python -m typoprint --help
```

## From source

```bash
git clone https://github.com/esandorfi/typoprint.git
cd typoprint
uv sync --locked
uv run typoprint --help
```

## First document

```bash
typoprint notes.md -o notes.pdf
```

```python
from typoprint import render, write_pdf

write_pdf(render("# Hello\n\nReady for print."), "hello.pdf")
```

Continue with the [command line guide](cli.md) or the
[template guide](extensions.md).
