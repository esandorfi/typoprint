// `editorial`: book-style serif print for reading and review.
// Only fonts embedded in the Typst wheel are used, so every host renders alike.
#let ink = luma(20)
#let muted = luma(105)
#let accent = rgb("#9a4a26")
#let rule = 0.5pt + muted

#import "foundations.typ": labels, french-spacing, byline, current-part, running-header, running-footer

// The cover gives the edition under the subtitle, e.g. `Version 0.4.0 · 2026-10-25`.
#let cover(meta) = page(header: none, footer: none, {
  v(1fr)
  text(size: 2.4em, smallcaps(meta.title))
  if meta.subtitle != none {
    v(0.6em)
    text(size: 1.3em, fill: muted, meta.subtitle)
  }
  let edition = (
    if meta.version != none [#labels.at(meta.lang).version #meta.version],
    meta.date,
  ).filter(part => part != none)
  if edition.len() > 0 {
    v(0.4em)
    text(fill: muted, edition.map(part => [#part]).join[ · ])
  }
  v(1.2em)
  line(length: 30%, stroke: 0.8pt + accent)
  v(0.6em)
  byline((author: meta.author))
  v(2fr)
})

#let document(meta, body) = {
  set std.document(
    title: meta.title,
    author: if meta.author != none { meta.author } else { () },
    date: none,
  )
  set page(
    paper: meta.paper,
    margin: (x: 25mm, top: 28mm, bottom: 25mm),
    header: running-header(meta),
    footer: running-footer(),
  )
  set text(
    font: "Libertinus Serif",
    size: 10.5pt,
    fill: ink,
    lang: meta.lang,
    hyphenate: true,
    costs: (widow: 100%, orphan: 100%),
  )
  set par(justify: true, leading: 0.62em, spacing: 1em)

  // Heading roles follow the chapter level: parts above it, sections below it.
  show heading: set text(weight: "semibold")
  show heading: it => {
    let base = meta.chapter-level
    if not it.outlined or it.level == base {
      block(above: 0pt, below: 1.2em, sticky: true, text(
        size: 1.75em,
        weight: "regular",
        smallcaps(it.body),
      ))
    } else if it.level < base {
      block(above: 0pt, below: 0.9em, sticky: true, {
        text(fill: accent, weight: "regular", smallcaps(it.body))
        v(-0.5em)
        line(length: 100%, stroke: 0.6pt + accent)
      })
    } else {
      let size = (1.25em, 1.08em).at(it.level - base - 1, default: 1em)
      block(above: 1.6em, below: 0.8em, sticky: true, text(size: size, smallcaps(it.body)))
    }
  }
  show outline.entry.where(level: 1): set block(above: 0.9em)
  show outline.entry.where(level: 1): set text(weight: "semibold")

  show link: set text(fill: accent)
  show raw: set text(font: "DejaVu Sans Mono", size: 0.86em)
  show raw.where(block: true): it => block(
    width: 100%,
    fill: luma(245),
    inset: 8pt,
    radius: 2pt,
    it,
  )
  show quote.where(block: true): it => block(
    stroke: (left: 1.2pt + accent),
    inset: (left: 10pt, y: 3pt),
    it.body,
  )
  set table(
    stroke: (_, y) => if y == 0 { (bottom: rule) },
    inset: (x: 6pt, y: 4pt),
    align: left,
  )
  show table.cell.where(y: 0): strong
  show table: it => {
    // Narrow columns: ragged text, and long identifiers may break after `._/`.
    set par(justify: false)
    show raw.where(block: false): code => {
      show regex("[._/]"): mark => [#mark.text#sym.zws]
      code
    }
    block(stroke: (y: 0.8pt + ink), inset: (y: 2pt), it)
  }
  set footnote.entry(separator: line(length: 30%, stroke: rule))

  show: it => if meta.lang == "fr" { french-spacing(it) } else { it }

  if meta.cover {
    cover(meta)
  } else if meta.toc {
    block(below: 1.6em, {
      text(size: 2em, smallcaps(meta.title))
      if meta.subtitle != none {
        linebreak()
        text(size: 1.2em, fill: muted, meta.subtitle)
      }
    })
  }
  if meta.toc {
    outline(title: labels.at(meta.lang).contents, depth: meta.toc-depth)
  }
  body
}

#let chapter(meta, body) = {
  pagebreak(weak: true)
  if meta.part != none {
    heading(level: meta.chapter-level - 1, meta.part)
  } else {
    // An opening page has no running header: it names the part the chapter is in.
    context {
      let part = current-part(meta)
      if part != none {
        block(below: 0.9em, sticky: true, text(size: 0.85em, fill: accent, smallcaps(part)))
      }
    }
  }
  [#metadata(meta.source) <typoprint-source>]
  if not meta.title-in-body {
    heading(level: meta.chapter-level, meta.title)
    byline(meta)
  }
  body
}

// Figure sizing belongs to the layout, independently of the diagram renderer.
#let diagram(body) = layout(size => {
  let natural = measure(body)
  let factor = calc.min(1, size.width / natural.width, 175mm / natural.height)
  assert(factor >= 0.5, message: "Diagramme trop dense pour ce gabarit : simplifier le diagramme.")
  align(center, scale(x: factor * 100%, y: factor * 100%, reflow: true, body))
})
