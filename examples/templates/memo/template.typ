// A complete layout written from scratch: no cover, no contents, one page style.
// It only needs the three exports `document`, `chapter`, and `diagram`.
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
  show link: set text(fill: rgb("#165d8d"))
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
