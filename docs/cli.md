# Command line reference

```text
typoprint [OPTIONS] [PATH ...]
python -m typoprint [OPTIONS] [PATH ...]
```

Every example below is copy-paste ready for a POSIX shell (bash, zsh) and runs
offline. Use `typoprint --help` for the live option list and `typoprint --version`
for the installed version.

## Quick start

```bash
# One file → notes.pdf (named after the file, written in the current directory)
typoprint notes.md

# Choose the output path (the folder must already exist)
typoprint notes.md -o build/notes.pdf

# A whole folder as one book, with a cover page
typoprint docs/ --recursive --cover -o handbook.pdf

# Preview what would be printed, without making a PDF
typoprint docs/ --recursive --dry-run
```

## Recipes

### Print several files in a chosen order

Files are printed in the order you list them. Each file becomes a chapter.

```bash
typoprint intro.md usage.md faq.md -o guide.pdf
```

### Print a folder

A folder contributes its `README.md` first, then the other `.md` files in natural
order (`chapter-2` before `chapter-10`).

```bash
typoprint docs/ -o handbook.pdf
typoprint docs/ --recursive -o handbook.pdf          # include subfolders
typoprint docs/ --recursive --by-folder -o book.pdf  # one part per folder
typoprint docs/ --recursive --exclude drafts --exclude "*/internal" -o public.pdf
```

### Control the order with a contents map

`--order` reads a Markdown file whose links define the chapters. Each `##` heading
opens a part.

```bash
cat > docs/CONTENTS.md <<'MAP'
## Getting started

- [Install](install.md)
- [First document](first.md)

## Reference

- [Command line](cli.md)
MAP

typoprint --order docs/CONTENTS.md -o handbook.pdf
typoprint --order docs/CONTENTS.md --strict -o handbook.pdf   # fail on unlisted pages
```

### Pipe through stdin and stdout

Stdin is UTF-8. With `-o -`, only PDF bytes go to stdout; messages go to stderr.

```bash
typoprint - -o notes.pdf < notes.md
cat notes.md | typoprint - -o - > notes.pdf
```

!!! note
    PowerShell versions differ in how pipelines treat native binary output. On
    Windows PowerShell, prefer file inputs and `-o notes.pdf`.

### Set metadata and layout

```bash
typoprint notes.md --title "Quarterly review" --subtitle "Q3" --author "Ada Lovelace" \
  --meta date=2026-10-31 --meta version=1.2 -o review.pdf

typoprint notes.md --template report --lang en --paper us-letter -o review.pdf
typoprint docs/ --cover --toc --toc-depth 3 -o handbook.pdf
typoprint notes.md --no-cover --no-toc -o brief.pdf
```

### Use a project config and presets

Create `typoprint.toml` in the folder you run from; it is picked up automatically.

```bash
cat > typoprint.toml <<'TOML'
[defaults]
template = "editorial"
lang = "en"
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
TOML

typoprint docs/ --preset handbook -o handbook.pdf
typoprint notes.md --preset brief -o brief.pdf
typoprint docs/ --config ci/typoprint.toml --preset handbook   # another file
typoprint docs/ --no-config                                    # ignore the file
```

Explicit command-line options beat the preset, which beats `[defaults]`, which beats
front matter, which beats built-in defaults.

### Customize the look

```bash
# Your own layout: a directory containing template.typ
typoprint notes.md --template ./my-template -o custom.pdf

# Pass JSON-valued options to the template (read as meta.template_options)
typoprint notes.md --template ./my-template \
  --template-option 'accent="#165d8d"' --template-option 'banner=true'

# Extra local fonts
typoprint notes.md --font-path ./fonts -o custom.pdf
```

See [Templates and content rules](extensions.md) for writing a template.

### Link to the web copy of unprinted files

Relative links to files that are not part of the PDF become plain text unless you
say where they are published:

```bash
typoprint docs/ --link-base https://example.com/docs/ -o handbook.pdf
```

### Use it in scripts and CI

```bash
set -euo pipefail
typoprint --order docs/CONTENTS.md --strict --preset handbook -o dist/handbook.pdf \
  || { echo "PDF build failed" >&2; exit 1; }

# Machine-readable plan: input order, parts, resolved settings, warnings
typoprint docs/ --recursive --dry-run > plan.json
```

## Options

### Input

| Option | Description |
| --- | --- |
| `PATH ...` | Markdown files or folders. `-` reads one UTF-8 document from stdin. |
| `-r`, `--recursive` | Include subfolders; a folder's files come before its subfolders. |
| `--exclude GLOB` | Skip a relative file or parent folder. Repeatable. An explicitly named file is always included. |
| `--by-folder` | Open a part at each folder change; filenames become chapters beneath it. |
| `--order MAP.md` | Use a contents map for order and parts. Replaces `PATH`, `--recursive`, and `--by-folder`. |
| `--strict` | With `--order`, refuse pages the map does not place. |

### Output

| Option | Description |
| --- | --- |
| `-o`, `--output PATH` | PDF destination. `-` writes PDF bytes to stdout. Default: first file stem or folder name in the current directory; `document.pdf` for stdin. |
| `--dry-run` | Print JSON (input order, parts, resolved settings, warnings) to stdout; write no PDF. |
| `--version` | Print the version and exit. |
| `-h`, `--help` | Show the option list and exit. |

### Settings

| Option | Description |
| --- | --- |
| `--config FILE` | Project TOML file. Default: `./typoprint.toml` if present. |
| `--no-config` | Ignore the project configuration. Mutually exclusive with `--config`. |
| `--preset NAME` | Apply a named preset; requires a configuration. |
| `--template NAME_OR_DIR` | `editorial` (default), `report`, or a directory containing `template.typ`. |
| `--lang {fr,en}` | Typography language. Default `fr`. |
| `--paper {a4,us-letter}` | Paper format. Default `a4`. |
| `--cover`, `--no-cover` | Add or omit a cover page. Default: no cover. |
| `--toc`, `--no-toc` | Add or omit the contents. Default: shown for multiple chapters. |
| `--toc-depth {1..6}` | Contents levels. Default `2`. |
| `--link-base URL` | HTTP(S) folder publishing the working directory. |
| `--font-path DIR` | Additional local font directory. Repeatable. System fonts are ignored. |
| `--template-option KEY=JSON` | Template option; values must be JSON. Repeatable, keys unique. |

### Metadata

| Option | Description |
| --- | --- |
| `--title`, `--subtitle`, `--author TEXT` | Override front matter. |
| `--meta KEY=VALUE` | Set `title`, `subtitle`, `author`, `date`, or `version`. Repeatable. |

A metadata field supplied twice in one invocation fails. Dates are never inferred
from the clock, file timestamps, or Git.

## Exit status and streams

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `2` | Usage, configuration, input, or rendering failure. |

Successful destinations, warnings, and errors go to **stderr**. Dry-run JSON and
`-o -` PDF bytes go to **stdout**, so redirecting stdout never captures messages.

## Behavior details

### Selecting inputs

| Input | Behavior |
| --- | --- |
| Files | Preserve argument order; duplicate selections fail |
| Folder | README first, other `.md` files in natural order |
| `--recursive` | Files of a folder precede its subfolders |
| `--by-folder` | Folder changes open parts; filenames become chapters beneath them |
| `--exclude GLOB` | Match relative files or their parent folders; repeatable |
| `--order MAP.md` | Map first, links under `##` headings define parts and chapters |
| `--strict` | With `--order`, refuse pages absent from the map |
| `-` | Read one UTF-8 Markdown document from stdin |
| `--dry-run` | JSON input order, part openings, resolved settings, and warnings |

Stdin cannot be mixed with file discovery. Explicit files are included even if
excluded by a folder glob. Map targets match exact spelling and case on every
platform. An empty selection, missing file, invalid UTF-8, or broken map target
fails before PDF output.

### Contents map parsing

The parser recognizes inline links in prose, lists, and tables. It ignores fenced
and inline code, images, external URLs, anchor-only links, and links outside the
map's directory. Duplicate links keep their first position. Directory links add
remaining pages recursively. Excluded links place no pages. Reference links and
deeply nested Markdown link syntax are outside this small ordering parser. The map
itself prints first unless excluded.

### Links in the PDF

Printed-file links resolve to the destination chapter or a known section anchor.
Links across chapters include `(p. N)` for paper readers. Missing or ambiguous
in-file anchors print as text; missing cross-file anchors fall back to the chapter.
Nonprinted relative files become text unless `--link-base URL` supplies the web
folder publishing the working directory. Its render root must lie under that
working directory. Existing HTTP(S) links remain active. For in-memory documents,
chapter names define internal links, while `link_base` is unavailable.

### Writing the output

`-o PATH` writes atomically and preserves the existing destination on a render or
replacement failure. The output directory must exist. An output resolving to a
selected input is refused.

### Dry runs

Dry-run parses front matter and resolves automatic choices but does not lay out
document bodies, load images, render diagrams, or execute custom layouts. It is an
input/settings inspection, not a guarantee that the eventual PDF can compile. It
performs no network requests with the supplied package set.

Front matter cannot select settings or executable code.
