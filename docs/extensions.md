# Templates and content rules

Templates control presentation; transformations and validators control Markdown.
Neither requires a plugin registry or application framework.

## Template bundle

A bundle is a directory containing `template.typ` and any local assets or helper
modules it imports. Select the directory with `--template ./templates/acme`,
`Settings(template="./templates/acme")`, or a config-relative `template` value.
Use `examples/template/` as a starting point.

```typst
#import "@local/typoprint:0.1.0": editorial, foundations

#let document(meta, body) = {
  show strong: set text(fill: rgb(meta.template_options.at("accent", default: "#9a4a26")))
  editorial.document(meta, body)
}
#let chapter = editorial.chapter
#let diagram = editorial.diagram
```

All three functions are required. The `document` function wraps the assembled
chapters; `chapter` receives one chapter; `diagram` sizes a Mermaid figure. Keep
figure readability checks when extending the built-in diagram function. Native
Typst set/show rules can change headings, tables, quotes, fonts, headers, and footers.

`meta` includes the rendering settings and resolved title, subtitle, author, date,
version, `toc`, `toc-depth`, `cover`, and `chapter-level`. A chapter additionally
receives `part`, `source`, `title-in-body`, `first`, and `document` (document-level
metadata). Chapter date/version come from that chapter's front matter. Templates
must tolerate missing optional metadata. Options are data, accessible through
`meta.template_options`; values must be JSON-compatible.

The reusable `foundations` module exports `labels`, `french-spacing`, `byline`,
`current-part`, `running-header`, and `running-footer`. Built-in `editorial` and
`report` modules expose their three layout functions. These resources belong to
the versioned `@local/typoprint:0.1.0` package, bundled with the Python distribution.
Keep its version aligned when upgrading Typoprint.

The renderer copies a custom bundle into an invocation-local Typst package named
`@local/typoprint-custom:0.1.0`; it supplies the package manifest. Bundle-local
imports and images stay inside that package. This does not widen the Markdown
image root. Fonts are selected by family name; use explicit `font_paths` to load
additional local fonts. System fonts remain disabled. The template bundle and
font directories are trusted local resources, not arbitrary uploaded code.

```toml
[defaults]
template = "templates/acme"
font_paths = ["fonts"]

[defaults.template_options]
accent = "#165d8d"
```

CLI options may be supplied as `--template-option 'accent="#165d8d"'`; values use
JSON syntax. Supplying template options at a higher precedence replaces the entire
options dictionary. Missing bundle files, missing exports, or Typst failures stop
rendering; there is no silent layout fallback.

Custom bundles must use already bundled packages and bundle-local dependencies for
offline operation. Typoprint does not install template dependencies. Keep custom
Typst code compatible with the pinned Typst compiler. No template path or font path
is accepted from Markdown front matter.

## Python content hooks

`render` and `render_files` accept `transforms: Sequence[Transform]` and
`validators: Sequence[Validator]`. A transform has signature `(markdown: str) -> str`;
a validator has signature `(markdown: str) -> None` and raises `RuleError` to refuse
input. Each chapter runs every transform in order, followed by every validator.
Front matter is part of the text passed through these hooks. Hook output is parsed
for titles and metadata after transformation.

Hook text is a fresh value; input files and `Document` values are never rewritten.
All chapters pass validation before compilation begins. Unexpected hook exceptions
become `RuleError` with a generic message; the original exception remains chained
for trusted debugging. A deliberately raised `RuleError` retains its developer
message. Do not put confidential text in messages intended for users.

There is no automatic callback discovery in configuration. Applications explicitly
import and pass their Python functions. CLI users needing Python rules can write a
small script around `render_files` and `write_pdf`.
