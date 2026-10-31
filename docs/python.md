# Python API reference

Typoprint's library and [CLI](cli.md) share one rendering pipeline. Install with
`pip install typoprint` (see [Install](install.md)). Everything below is importable
from the top-level package:

```python
from typoprint import (
    Chapter, Document, Settings,                       # inputs
    render, render_files, plan_files, write_pdf,       # actions
    load_settings,                                     # configuration
    PrintPlan, PlannedFile, RenderResult,              # results
    Transform, Validator,                              # callback types
    TypoprintError, ConfigurationError, RenderError, RuleError,  # errors
)
```

Calls are synchronous, offline, and isolated: each call owns its compiler and
temporary files, and never modifies your sources or writes an output file.

## Quick start

```python
from typoprint import render, write_pdf

result = render("# Hello\n\nReady for print.")
write_pdf(result, "hello.pdf")
```

`RenderResult.content` is the PDF as `bytes`; `RenderResult.warnings` is a tuple
of strings.

## Choose your entry point

| You have… | Use |
| --- | --- |
| A Markdown string in memory | `render("# Title…")` |
| Several in-memory chapters, maybe with images | `render(Document(...), assets=...)` |
| Files or folders on disk | `render_files(["notes.md"])` |
| A need to inspect order first | `plan_files(...)` then `render_files(plan)` |

## Render a string

```python
from typoprint import Settings, render

result = render("# Hello\n\nReady for print.")

result = render(
    "# Hello",
    settings=Settings(template="report", lang="en", paper="us-letter", cover=True),
)
```

## Render files and folders

`render_files` takes the same discovery options as the CLI.

```python
from typoprint import Settings, render_files, write_pdf

result = render_files(["notes.md"])                          # one file
result = render_files(["intro.md", "usage.md", "faq.md"])    # chosen order
result = render_files(["docs"], recursive=True)              # a folder tree
result = render_files(["docs"], recursive=True, by_folder=True)   # parts per folder
result = render_files(["docs"], recursive=True, exclude=["drafts", "*/internal"])
result = render_files(order="docs/CONTENTS.md", strict=True)      # contents map
result = render_files(
    ["docs"], recursive=True, settings=Settings(template="report", lang="en")
)
write_pdf(result, "handbook.pdf")
```

`order` replaces `paths`, `recursive`, and `by_folder`; `strict` requires `order`.
See [contents maps](cli.md#control-the-order-with-a-contents-map) for the map format.
Warnings from planning (for example unplaced pages) are included in
`result.warnings`.

## Inspect before printing

`plan_files` is the Python equivalent of `--dry-run`: it resolves the exact file
order and part openings without compiling. Pass the plan back to `render_files`
to print precisely what you inspected.

```python
from typoprint import plan_files, render_files, write_pdf

plan = plan_files(["docs"], recursive=True, by_folder=True)
print(plan.root, plan.warnings)
for planned in plan.files:
    print(planned.part, planned.path)

write_pdf(render_files(plan), "handbook.pdf")
```

A `PrintPlan` replaces discovery options: passing `recursive`, `exclude`, `order`,
`by_folder`, or `strict` together with a plan raises `ConfigurationError`.

## Multiple chapters and images in memory

```python
from pathlib import Path
from typoprint import Chapter, Document, render

document = Document(
    chapters=(
        Chapter(
            name="intro.md",
            part="Basics",
            markdown="# Intro\n\n![Chart](images/chart.png)",
        ),
        Chapter(name="results.md", markdown="# Results\n\nSee [intro](intro.md)."),
    )
)
result = render(document, assets={"images/chart.png": Path("chart.png").read_bytes()})
```

- `Chapter.name` is a relative POSIX path (no `..`, drive, or backslash) and must be
  unique within a `Document`. Chapter names define internal links.
- `Chapter.part` opens a named part (book section) at that chapter.
- Images resolve relative to each chapter's name. In-memory rendering sees only the
  `assets` you supply, never host paths. Remote images are refused.
- `link_base` is unavailable for in-memory documents.

## Settings

`Settings` is an immutable, validated model. Unknown fields are rejected.

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `template` | `str` | `"editorial"` | `"editorial"`, `"report"`, or a template directory |
| `title`, `subtitle`, `author`, `date`, `version` | `str \| None` | `None` | Metadata; `None` inherits front matter |
| `lang` | `"fr" \| "en"` | `"fr"` | Typography language |
| `paper` | `"a4" \| "us-letter"` | `"a4"` | Paper format |
| `cover` | `bool` | `False` | Cover page |
| `toc` | `bool \| None` | `None` | Contents; `None` shows it for multiple chapters |
| `toc_depth` | `int` (1–6) | `2` | Contents levels |
| `link_base` | `str \| None` | `None` | HTTP(S) folder publishing the sources (files only) |
| `font_paths` | `tuple[Path, ...]` | `()` | Extra local font directories |
| `template_options` | `dict[str, JSON]` | `{}` | Options read by templates as `meta.template_options` |

Titles come from `title`, then front matter, then the first H1, then the filename.
Front matter may supply `title`, `subtitle`, `author`, `date`, and `version`.
Dates are never inferred from the clock, file timestamps, or Git.

### Layering settings

`render` and `render_files` accept both `settings` (a base) and `overrides`. Only
fields you **explicitly set** on `overrides` win, so `False` stays `False`:

```python
from typoprint import Settings, render

house_style = Settings(template="report", lang="en", cover=True)
result = render("# Memo", settings=house_style, overrides=Settings(cover=False))
```

`template_options` replace as a unit rather than merging key by key.

### Load a project file

Library calls never discover `typoprint.toml`; load it explicitly. Relative paths in
the TOML belong to the TOML file's folder. Unknown keys and presets raise
`ConfigurationError`.

```python
from typoprint import Settings, load_settings, render

settings = load_settings("typoprint.toml")                      # [defaults] only
settings = load_settings("typoprint.toml", preset="handbook")   # plus a preset
result = render("# Introduction", settings=settings, overrides=Settings(cover=False))
```

Precedence: `overrides` → preset → `[defaults]` → front matter → built-in defaults.
See the [CLI page](cli.md#use-a-project-config-and-presets) for the TOML layout.

## Custom templates and options

```python
from typoprint import Settings, render

result = render(
    "# Custom",
    settings=Settings(
        template="./my-template",                      # directory with template.typ
        template_options={"accent": "#165d8d", "banner": True},
        font_paths=("./fonts",),
    ),
)
```

See [Templates and content rules](extensions.md) for writing a template.

## Transforms and validators

Explicit callbacks run on each chapter's Markdown: all `transforms` first, in
order, then all `validators`. Sources are never rewritten.

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

`transforms` and `validators` also work with `render_files`. A transform must return
`str`. Any other exception from a callback is wrapped as `RuleError` without the
original message, which may contain confidential Markdown. TOML and Markdown never
import callbacks, and Markdown cannot execute embedded Typst; callbacks and templates
are trusted developer code.

## Write the PDF

```python
from pathlib import Path
from typoprint import write_pdf

path = write_pdf(result, "build/out.pdf")      # returns the resolved Path
Path("build/out.pdf").read_bytes()[:5]         # b'%PDF-'
```

`write_pdf` flushes a complete PDF to a temporary file then replaces the destination
atomically, so a failure never leaves a truncated file. The folder must exist. Or
skip it and use `result.content` directly (HTTP response, object storage, …).

## Handle errors

All library errors derive from `TypoprintError` (a `ValueError`).

| Error | Raised for |
| --- | --- |
| `ConfigurationError` | Invalid settings, template bundle, or config file |
| `RenderError` | Invalid inputs, unreadable files, failed compilation, failed write |
| `RuleError` | A transform or validator refused or failed |

```python
from typoprint import RuleError, TypoprintError, render

try:
    result = render("# Doc")
except RuleError:
    ...  # your rule rejected the content
except TypoprintError:
    ...  # anything else the library raised
```

Compiler diagnostics can quote Markdown, so HTTP adapters should return a generic
message and keep details private.

## Embedding in applications

Rendering is CPU-bound and synchronous. From an async framework, offload it:

```python
import asyncio
from typoprint import render


async def to_pdf(markdown: str) -> bytes:
    result = await asyncio.to_thread(render, markdown)
    return result.content
```

For CPU parallelism or hard timeouts use separate processes. Runnable examples:
[HTTP API](https://github.com/esandorfi/typoprint/blob/main/examples/api.py) and
[process worker](https://github.com/esandorfi/typoprint/blob/main/examples/worker.py).

## Reproducibility

With identical inputs, settings, fonts, templates, and pinned dependencies, repeated
renders produce identical PDF bytes. System fonts are ignored. French spacing, local
links with page references, footnotes, tables, code highlighting, and Mermaid share
one pipeline across layouts. PDF accessibility tags stay enabled; this does not
certify every document against an accessibility standard.

Custom templates can execute Typst and custom Python callbacks have ordinary Python
privileges; only deploy extensions you trust. Bundle dependencies locally before
offline use. Content-aware layout selection, LaTeX math, arbitrary HTML/CSS, remote
asset fetching, a hosted service, and TypeScript bindings are outside this release.
