// Shared print furniture; each layout supplies its own colours and typography.
#let muted = luma(105)
#let rule = 0.5pt + muted

#let labels = (
  fr: (contents: "Sommaire", version: "Version"),
  en: (contents: "Contents", version: "Version"),
)

// French typography: narrow no-break space before `;:!?»` and after `«`.
// Code and links keep their original spacing.
#let french-spacing(body) = {
  show regex("[ \u{00A0}][;:!?»]"): it => [#sym.space.nobreak.narrow#it.text.clusters().last()]
  show regex("«[ \u{00A0}]"): [«#sym.space.nobreak.narrow]
  show raw: it => {
    show sym.space.nobreak.narrow: " "
    it
  }
  show link: it => {
    show sym.space.nobreak.narrow: " "
    it
  }
  body
}

#let byline(meta, muted: muted) = {
  let parts = (meta.at("author", default: none), meta.at("date", default: none))
    .filter(part => part != none)
    .map(part => [#part])
  if parts.len() > 0 {
    block(below: 1.6em, text(size: 0.9em, fill: muted, smallcaps(parts.join[ · ])))
  }
}

// The part opened last before the current position, if the document has parts.
#let current-part(meta) = if meta.chapter-level > 1 {
  let parts = query(heading.where(level: meta.chapter-level - 1, outlined: true).before(here()))
  if parts.len() > 0 { parts.last().body }
}

// Chapter pages carry their title on top; other pages show where the reader is:
// the part, else the document title, and the chapter.
#let running-header(meta, muted: muted, rule: rule, caps: smallcaps) = context {
  let current = here().page()
  let opens = query(heading.where(outlined: true)).any(it => (
    it.level <= meta.chapter-level and it.location().page() == current
  ))
  let previous = query(heading.where(level: meta.chapter-level).before(here()))
  if not opens and previous.len() > 0 {
    let part = current-part(meta)
    set text(size: 8pt, fill: muted)
    grid(
      columns: (1fr, auto),
      column-gutter: 1em,
      caps(if part != none { part } else { meta.title }), caps(previous.last().body),
    )
    v(-0.5em)
    line(length: 100%, stroke: rule)
  }
}

// Every chapter page names its source file, so a printed page leads back to it.
#let running-footer(muted: muted) = context {
  let current = here().page()
  let sources = query(<typoprint-source>).filter(it => it.location().page() <= current)
  set text(size: 8pt, fill: muted)
  grid(
    columns: (1fr, auto),
    column-gutter: 1em,
    if sources.len() > 0 { text(font: "DejaVu Sans Mono", size: 7pt, sources.last().value) },
    counter(page).display("1 / 1", both: true),
  )
}
