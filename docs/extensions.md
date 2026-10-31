# Templates and content rules

Templates control presentation; transformations and validators control Markdown.
Neither requires a plugin registry or application framework.

Typoprint templates are plain [Typst](https://typst.app/docs/) code. If you can
write a Typst `set` or `show` rule, you can restyle every document. See
[Learn Typst](#learn-typst) for the references that matter.

## Built-in templates

Two layouts ship with the package. Pick one with `--template`, `Settings(template=...)`,
or `template = "..."` in `typoprint.toml`.

| | `editorial` (default) | `report` |
| --- | --- | --- |
| Feel | Book-style reading and review | Compact, modern reports |
| Body font | Libertinus Serif, justified | Source Sans 3, ragged right |
| Headings | Small caps, accent rules for parts | Bold sans, numbered `1.1` |
| Accent | Terracotta `#9a4a26` | Blue `#165d8d` |
| Title | Serif title page, or a title above the contents | Tinted title block with a left bar |
| Tables | Open, ruled header | Filled header, striped rows |
| Quotes | Left rule | Tinted panel |

Both share the same content pipeline, so French spacing, local links with page
references, footnotes, tables, syntax-highlighted code, and Mermaid diagrams behave
identically. Both support covers, contents, parts, A4 or US Letter, and French or
English labels.

```bash
typoprint notes.md                         # editorial
typoprint notes.md --template report       # report
typoprint docs/ --template report --cover --toc -o handbook.pdf
```

## Your own templates

A template is a **bundle**: a directory containing `template.typ`, plus any helper
`.typ` modules, images, or data files it uses. Select it by path:

```bash
typoprint notes.md --template ./templates/acme -o acme.pdf
```

```python
from typoprint import Settings, render

result = render("# Hi", settings=Settings(template="./templates/acme"))
```

```toml
[defaults]
template = "templates/acme"   # relative to this TOML file
```

There are three levels of ambition. Each has a complete, tested example in
[`examples/`](https://github.com/esandorfi/typoprint/tree/main/examples).

| Goal | Approach | Example |
| --- | --- | --- |
| Change a color, font, or rule | Wrap a built-in layout and add `set`/`show` rules | [`template/`](https://github.com/esandorfi/typoprint/tree/main/examples/template), [`confidential/`](https://github.com/esandorfi/typoprint/tree/main/examples/templates/confidential) |
| Brand it: logo, cover, helper modules | Wrap a built-in layout and replace parts of it | [`branded/`](https://github.com/esandorfi/typoprint/tree/main/examples/templates/branded) |
| Total control | Write all three functions yourself | [`memo/`](https://github.com/esandorfi/typoprint/tree/main/examples/templates/memo) |

### The contract

`template.typ` must export three functions. A missing export stops rendering with a
clear error; there is no silent fallback.

| Export | Receives | Responsibility |
| --- | --- | --- |
| `document(meta, body)` | Document metadata, all chapters | Page setup, fonts, show rules, title or cover, contents |
| `chapter(meta, body)` | Chapter metadata, one chapter | Page break, part heading, chapter title |
| `diagram(body)` | A rendered Mermaid figure | Size and place the figure |

`meta` for `document` carries the resolved settings and metadata:

| Field | Meaning |
| --- | --- |
| `title`, `subtitle`, `author`, `date`, `version` | Resolved metadata, or `none` |
| `lang`, `paper` | `"fr"`/`"en"`, `"a4"`/`"us-letter"` |
| `cover`, `toc`, `toc-depth` | Whether to print a cover and contents, and its depth |
| `chapter-level` | Heading level of chapter titles: `1`, or `2` when the document has parts |
| `template_options` | Your JSON-compatible options dictionary |
| `link_base`, `font_paths`, `template` | Remaining settings |

`meta` for `chapter` has the same fields, and in addition:

| Field | Meaning |
| --- | --- |
| `title` | The chapter title as content |
| `title-in-body` | `true` when the Markdown already opens with its own H1 |
| `part` | Part name when this chapter opens a part, else `none` |
| `source` | Source file name, for running footers |
| `first` | `true` for the first chapter |
| `document` | The document-level `meta` above |

A chapter's `date` and `version` come from that chapter's own front matter. Templates
must tolerate missing optional metadata (`none`).

### Recipe: tweak a built-in layout

The smallest template wraps `editorial` or `report` and adds Typst rules before
delegating.

```typst
// templates/acme/template.typ
#import "@local/typoprint:0.1.0": editorial

#let document(meta, body) = {
  show strong: set text(fill: rgb(meta.template_options.at("accent", default: "#165d8d")))
  editorial.document(meta, body)
}
#let chapter = editorial.chapter
#let diagram = editorial.diagram
```

Start from [`examples/template/`](https://github.com/esandorfi/typoprint/tree/main/examples/template).

### Recipe: add a watermark

Styles that the built-in layout does not set yourself, such as `page.background`,
survive when you set them before delegating:

```typst
#import "@local/typoprint:0.1.0": report

#let document(meta, body) = {
  let options = meta.template_options
  let label = options.at("label", default: "CONFIDENTIAL")
  let tint = rgb(options.at("accent", default: "#b3261e")).transparentize(88%)
  set page(background: rotate(-30deg, text(size: 72pt, weight: "bold", fill: tint, label)))
  report.document(meta, body)
}
#let chapter = report.chapter
#let diagram = report.diagram
```

```bash
typoprint notes.md --template examples/templates/confidential \
  --template-option 'label="DRAFT"' -o draft.pdf
```

!!! note
    A built-in layout's own `set` rules run later and win over yours. To change
    something it already sets, such as the font, put your rule *inside* the body you
    hand over, where it runs after the layout's:

    ```typst
    #let document(meta, body) = editorial.document(meta, {
      set text(font: "DejaVu Sans Mono")
      body
    })
    ```

    For page-level changes such as margins or the header, start from scratch.

### Recipe: brand it with a logo and cover

A bundle may contain helper modules and assets. Imports and images resolve inside the
bundle, so they never widen what Markdown can read.

```text
templates/branded/
├── template.typ
├── brand.typ      # helper module
└── logo.svg       # bundle-local asset
```

```typst
// brand.typ
#let default-accent = rgb("#0b6e4f")
#let logo(width: 28mm) = image("logo.svg", width: width)
```

```typst
// template.typ
#import "@local/typoprint:0.1.0": editorial
#import "brand.typ"

#let document(meta, body) = {
  let options = meta.template_options
  let accent = rgb(options.at("accent", default: brand.default-accent.to-hex()))
  show heading: set text(fill: accent)
  show link: set text(fill: accent)
  // Replace the built-in cover by our own, then let `editorial` do the rest.
  let inner = meta + (cover: false)
  if meta.cover {
    page(header: none, footer: none, {
      brand.logo(width: 40mm)
      v(1fr)
      text(size: 2.6em, weight: "bold", fill: accent, meta.title)
      if meta.subtitle != none { linebreak(); text(size: 1.2em, meta.subtitle) }
      v(1em)
      text(options.at("company", default: "Acme") + if meta.author != none { " · " + meta.author } else { "" })
      v(1fr)
    })
  }
  editorial.document(inner, body)
}
#let chapter = editorial.chapter
#let diagram = editorial.diagram
```

```bash
typoprint docs/ --cover --template examples/templates/branded \
  --template-option 'company="Acme Inc"' --template-option 'accent="#0b6e4f"' \
  -o branded.pdf
```

### Recipe: write a layout from scratch

You can ignore `editorial` and `report` entirely. Reuse the shared
[building blocks](#building-blocks) for the parts you do not want to rewrite.

```typst
#import "@local/typoprint:0.1.0": foundations

#let document(meta, body) = {
  set std.document(title: meta.title, author: if meta.author != none { meta.author } else { () })
  set page(
    paper: meta.paper,
    margin: (x: 28mm, y: 24mm),
    header: foundations.running-header(meta),
    footer: foundations.running-footer(),
  )
  set text(font: "Libertinus Serif", size: 11pt, lang: meta.lang)
  set par(justify: true)
  show heading: set text(font: "DejaVu Sans Mono", weight: "regular")
  show: it => if meta.lang == "fr" { foundations.french-spacing(it) } else { it }

  // Letterhead instead of a title page.
  text(size: 1.6em, weight: "bold", meta.title)
  if meta.subtitle != none { linebreak(); text(fill: foundations.muted, meta.subtitle) }
  v(0.4em)
  foundations.byline(meta)
  line(length: 100%, stroke: foundations.rule)
  body
}

#let chapter(meta, body) = {
  pagebreak(weak: true)
  [#metadata(meta.source) <typoprint-source>]   // lets the footer name the source file
  if not meta.title-in-body { heading(level: meta.chapter-level, meta.title) }
  body
}

#let diagram(body) = align(center, body)
```

Full file: [`examples/templates/memo/`](https://github.com/esandorfi/typoprint/tree/main/examples/templates/memo).

!!! tip
    Honor `meta.cover` and `meta.toc` if you want `--cover` and `--toc` to keep
    working, and keep a `diagram` that scales wide figures down to the page. The
    built-in `diagram` refuses figures it would have to shrink below 50%.

## Building blocks

Everything below comes from the versioned `@local/typoprint:0.1.0` package, bundled
with the Python distribution. Keep the version aligned when upgrading Typoprint.

```typst
#import "@local/typoprint:0.1.0": editorial, report, foundations
```

| Module | Exports |
| --- | --- |
| `editorial` | `document`, `chapter`, `diagram`, `cover(meta)`, and the palette `ink`, `muted`, `accent`, `rule` |
| `report` | `document`, `chapter`, `diagram`, `title-block(meta)`, and the palette `ink`, `muted`, `accent`, `pale`, `rule` |
| `foundations` | `labels`, `french-spacing`, `byline`, `current-part`, `running-header`, `running-footer`, `muted`, `rule` |

| `foundations` item | Use |
| --- | --- |
| `labels` | `labels.at(meta.lang)` gives translated `contents` and `version` words |
| `french-spacing(body)` | French narrow no-break spaces before `;:!?»` and after `«`; leaves code and links alone |
| `byline(meta)` | Author and date line |
| `current-part(meta)` | The part the reader is in, or `none` |
| `running-header(meta)` | Header naming the part or title and the chapter, hidden on opening pages |
| `running-footer()` | Footer with the source file name and `page / total` |

## Options, fonts, and configuration

Options are data your template reads from `meta.template_options`; values must be
JSON-compatible. Supply them from any entry point:

```bash
typoprint notes.md --template ./templates/acme --template-option 'accent="#165d8d"'
```

```python
from typoprint import Settings

settings = Settings(
    template="./templates/acme",
    template_options={"accent": "#165d8d"},
    font_paths=("./fonts",),
)
```

```toml
[defaults]
template = "templates/acme"
font_paths = ["fonts"]

[defaults.template_options]
accent = "#165d8d"
```

Supplying template options at a higher precedence replaces the entire dictionary.

Fonts are selected by family name inside Typst (`set text(font: "...")`). Typoprint
uses only the fonts bundled with the package (Typst's embedded fonts and Source
Sans 3) so every host renders alike; system fonts are disabled. Load more with
`--font-path DIR` or `font_paths`, and keep font licenses beside the files.

## How bundles are loaded

The renderer copies a custom bundle into an invocation-local Typst package named
`@local/typoprint-custom:0.1.0`; it supplies the package manifest. Bundle-local
imports and images stay inside that package and do not widen the Markdown image
root. The template bundle and font directories are trusted local resources, not
arbitrary uploaded code. Missing bundle files, missing exports, or Typst failures
stop rendering.

Custom bundles must use already bundled packages (`@preview/cmarker`,
`@preview/merman`, and `@local/typoprint`) and bundle-local dependencies for offline
operation. Typoprint does not install template dependencies. Keep custom Typst code
compatible with the pinned Typst compiler. No template path or font path is accepted
from Markdown front matter.

## Learn Typst

Typoprint compiles with the open-source [Typst](https://typst.app/) engine. These are
the pages you will use most when writing a template:

| Topic | Link |
| --- | --- |
| Start here: the Typst tutorial | [typst.app/docs/tutorial](https://typst.app/docs/tutorial/) |
| `set` and `show` rules: restyle anything | [Styling reference](https://typst.app/docs/reference/styling/) |
| Advanced styling tutorial (headers, numbering, templates) | [Advanced styling](https://typst.app/docs/tutorial/advanced-styling/) |
| Writing a template: functions with arguments | [Making a template](https://typst.app/docs/tutorial/making-a-template/) |
| Page size, margins, header, footer, background | [`page`](https://typst.app/docs/reference/layout/page/) |
| Fonts, size, language, hyphenation | [`text`](https://typst.app/docs/reference/text/text/) |
| Paragraph spacing and justification | [`par`](https://typst.app/docs/reference/model/par/) |
| Headings and numbering | [`heading`](https://typst.app/docs/reference/model/heading/) |
| Tables | [`table`](https://typst.app/docs/reference/model/table/) |
| Contents | [`outline`](https://typst.app/docs/reference/model/outline/) |
| Images | [`image`](https://typst.app/docs/reference/visualize/image/) |
| Code blocks | [`raw`](https://typst.app/docs/reference/text/raw/) |
| Scripting: variables, functions, `if`, loops | [Scripting](https://typst.app/docs/reference/scripting/) |
| Reading page state in headers and footers | [Context](https://typst.app/docs/reference/context/) |
| Everything else | [Full reference](https://typst.app/docs/reference/) |
| Community packages (bundle only what you vendor) | [Typst Universe](https://typst.app/universe/) |

Typoprint's Markdown reader is [cmarker](https://typst.app/universe/package/cmarker)
and diagrams come from [merman](https://typst.app/universe/package/merman), both
vendored with their licenses in the package.

## Python content hooks

`render` and `render_files` accept `transforms: Sequence[Transform]` and
`validators: Sequence[Validator]`. A transform has signature `(markdown: str) -> str`;
a validator has signature `(markdown: str) -> None` and raises `RuleError` to refuse
input. Each chapter runs every transform in order, followed by every validator.
Front matter is part of the text passed through these hooks. Hook output is parsed
for titles and metadata after transformation.

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

Hook text is a fresh value; input files and `Document` values are never rewritten.
All chapters pass validation before compilation begins. Unexpected hook exceptions
become `RuleError` with a generic message; the original exception remains chained
for trusted debugging. A deliberately raised `RuleError` retains its developer
message. Do not put confidential text in messages intended for users.

There is no automatic callback discovery in configuration. Applications explicitly
import and pass their Python functions. CLI users needing Python rules can write a
small script around `render_files` and `write_pdf`. See the
[Python API](python.md) for the full reference.
