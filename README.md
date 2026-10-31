# Typoprint

**Markdown in. Beautiful PDFs out.**

Typoprint is a small Python library and CLI for offline Markdown printing, powered by
Typst. Use it in a terminal, API, worker, or script. No browser, TeX installation,
external compiler process, or network connection is needed to render.

Python **3.13+** is required. Rendering resources, Mermaid support, and fonts ship
with the package. Windows, Linux with glibc, and macOS are supported; Alpine/musl is
outside the tested wheel platforms.

## Install

From PyPI:

```bash
uv tool install typoprint   # CLI in its own environment (or: pipx install typoprint)
pip install typoprint       # library in the current environment (or: uv add typoprint)
```

From a checkout:

```bash
uv sync --locked
uv run typoprint --help
```

Documentation: <https://esandorfi.github.io/typoprint/>. Contributions are welcome;
see [CONTRIBUTING.md](CONTRIBUTING.md). Releases are published by maintainers; see
[releasing](docs/releasing.md).

## CLI

```bash
typoprint notes.md -o notes.pdf
typoprint docs/ --recursive --cover -o handbook.pdf
typoprint --order docs/README.md --strict --dry-run
typoprint docs/ --config typoprint.toml --preset handbook
typoprint notes.md --template report --lang en --paper us-letter
typoprint - -o - < notes.md > notes.pdf
```

The last example uses a POSIX shell or `cmd.exe` for byte-preserving redirection.
In PowerShell, use file inputs and `-o notes.pdf`; PowerShell versions differ in
how pipelines handle native binary output. Stdin is UTF-8; `-o -` writes only PDF
bytes to stdout. Paths, warnings, and errors go to stderr. Errors return code 2.

Each file becomes a chapter. A directory contributes `README.md`, then other
Markdown files in natural order (`chapter-2` before `chapter-10`). `--recursive`
adds subfolders. `--exclude` accepts repeatable relative globs; an explicitly named
file is always included. `--by-folder` opens parts at folder changes.

`--order CONTENTS.md` reads local Markdown links under each `##` heading as chapter
order and part names. Folder links expand recursively. Code, images, web links,
and links outside the contents folder do not place pages. Unplaced pages follow
with a warning; `--strict` refuses them. The contents file itself prints first
unless excluded. This preserves the source feature's inline-link parser; reference
links do not place pages. See [CLI behavior](docs/cli.md).

## Python

```python
from typoprint import Settings, render, render_files, write_pdf

result = render("# Hello\n\nReady for print.")
write_pdf(result, "hello.pdf")

result = render_files(
    ["docs"],
    recursive=True,
    exclude=["drafts"],
    settings=Settings(template="report", lang="en"),
)
```

`RenderResult.content` is PDF bytes; `RenderResult.warnings` is a tuple of strings.
Rendering never writes an output file. `write_pdf` replaces the destination
atomically after flushing the complete PDF. It requires an existing output folder.

For multiple in-memory chapters and explicitly supplied images:

```python
from pathlib import Path
from typoprint import Chapter, Document, render

document = Document(
    chapters=(
        Chapter(name="intro.md", markdown="# Intro\n\n![Chart](images/chart.png)"),
        Chapter(name="results.md", markdown="# Results\n\nSee [intro](intro.md)."),
    )
)
result = render(document, assets={"images/chart.png": Path("chart.png").read_bytes()})
```

Asset names are relative POSIX paths. Images resolve relative to each chapter's
name. In-memory rendering sees only explicitly supplied assets, never paths on
the host. Filesystem rendering resolves images inside the common input root,
rejects symlinks escaping it, and snapshots referenced images before compilation.
Remote images are refused. Mermaid blocks render locally; invalid or unreadable
diagrams fail explicitly.

The public API exports `Chapter`, `Document`, `Settings`, `PrintPlan`, `PlannedFile`,
`RenderResult`, `Transform`, `Validator`, `TypoprintError`, `ConfigurationError`,
`RenderError`, `RuleError`, and the five main functions. `python -m typoprint`
provides the same CLI. See runnable [HTTP API](examples/api.py) and
[process worker](examples/worker.py) examples.

## Smart settings

Create `typoprint.toml`:

```toml
[defaults]
template = "editorial"
lang = "fr"
paper = "a4"

[presets.handbook]
cover = true
toc = true
toc_depth = 2
title = "Engineering handbook"

[presets.brief]
template = "report"
cover = false
toc = false
```

Precedence is explicit overrides → selected preset → defaults → supported
front-matter metadata → built-in defaults. An explicit `false` stays false.
Unspecified fields inherit; `None` for optional metadata also inherits.

The CLI looks only for `typoprint.toml` in its working directory. `--config` selects
another file; `--no-config` disables discovery. Library calls never discover a file:

```python
from typoprint import Settings, load_settings, render

settings = load_settings("typoprint.toml", preset="handbook")
result = render("# Introduction", settings=settings, overrides=Settings(cover=False))
```

Defaults are `editorial`, French, A4, no cover, contents for multiple chapters,
and contents depth 2. Titles use front matter, then the first H1, then the filename.
Front matter may supply `title`, `subtitle`, `author`, `date`, and `version`; chapter
dates and versions remain local to each chapter. Dates are never inferred from
the clock, filesystem timestamps, or Git.

Configuration can also specify `link_base`, `font_paths`, and `template_options`.
Paths in TOML belong to the TOML file's folder. Unknown keys and presets fail.
Nested `template_options` replace as a unit when layering settings. Dry runs emit
JSON containing input order, parts, effective metadata/settings, and warnings.

## Extend

Use built-in `editorial` for book-style reading or `report` for compact sans-serif
reports. Supply a template directory with `template.typ` to define another layout.
It exports `document(meta, body)`, `chapter(meta, body)`, and `diagram(body)`.
Built-in layouts and foundations are reusable through the versioned local Typst
package. Custom options live in `meta.template_options`.

Python callers may also supply explicit transformations and validators:

```python
from typoprint import RuleError, render


def require_summary(markdown: str) -> None:
    if "## Summary" not in markdown:
        raise RuleError("A Summary section is required")


result = render(
    "# Draft\n\n## Summary\n\n{{product}} is ready.",
    transforms=[lambda text: text.replace("{{product}}", "Typoprint")],
    validators=[require_summary],
)
```

All transforms run before validators for each chapter. Sources remain unchanged.
Callbacks and templates are trusted developer code, supplied by the application;
TOML and Markdown never import Python callbacks. Markdown cannot execute embedded
Typst. See the [extension guide](docs/extensions.md) and
[starter template](examples/template/template.typ).

## Reproducibility and embedding

With identical inputs, settings, fonts, templates, and pinned dependencies,
repeated renders produce identical PDF bytes. System fonts are ignored. French
spacing, local links with page references, footnotes, tables, code highlighting,
and Mermaid share one pipeline across layouts. PDF accessibility tags remain
enabled; this does not certify every document against an accessibility standard.

Library calls are synchronous. An async API should offload rendering from its event
loop. A worker can use separate processes for CPU parallelism and caller-managed
timeouts. Each call owns its compiler and temporary files; callback state remains
the caller's responsibility. Compiler errors and warnings can quote Markdown, so
HTTP adapters should return generic messages and keep detailed diagnostics private.
Custom templates can execute Typst and custom Python callbacks have ordinary Python
privileges; only deploy extensions you trust. Bundle dependencies locally before
offline use. Automatic content-aware layout selection, LaTeX math rendering,
arbitrary HTML/CSS, remote asset fetching, a hosted service, and TypeScript bindings
are outside this release.

## Develop

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv build
```

[Verification](docs/verification.md) describes clean-wheel and offline checks.
MIT covers first-party code. Bundled packages and fonts retain their own licenses;
see [third-party notices](THIRD_PARTY_NOTICES.md).
