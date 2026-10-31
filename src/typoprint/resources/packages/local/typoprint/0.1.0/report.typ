// `report`: a compact sans-serif report; Markdown stays in the shared pipeline.
// Source Sans 3 is vendored with its OFL licence in print/fonts/source-sans-3/.
#import "foundations.typ": labels, french-spacing, byline, current-part, running-header, running-footer

#let ink = rgb("#203449")
#let muted = rgb("#526578")
#let accent = rgb("#165d8d")
#let pale = rgb("#eef4f8")
#let rule = 0.5pt + rgb("#c9d8e3")

#let title-block(meta) = block(
  width: 100%, fill: pale, inset: 16pt, below: 1.8em,
  stroke: (left: 3pt + accent),
  {
    text(size: 2em, weight: "bold", fill: ink, meta.title)
    if meta.subtitle != none {
      v(0.5em)
      text(size: 1.15em, fill: muted, meta.subtitle)
    }
    let edition = (
      meta.author,
      if meta.version != none [#labels.at(meta.lang).version #meta.version],
      meta.date,
    ).filter(part => part != none)
    if edition.len() > 0 {
      v(0.7em)
      text(size: 0.9em, fill: muted, edition.map(part => [#part]).join[ · ])
    }
  },
)

#let document(meta, body) = {
  set std.document(
    title: meta.title,
    author: if meta.author != none { meta.author } else { () },
    date: none,
  )
  set page(
    paper: meta.paper,
    margin: (x: 22mm, top: 25mm, bottom: 23mm),
    header: running-header(meta, muted: muted, rule: rule, caps: body => body),
    footer: running-footer(muted: muted),
  )
  set text(
    font: "Source Sans 3", size: 10.5pt, fill: ink,
    lang: meta.lang, hyphenate: true,
    costs: (widow: 100%, orphan: 100%),
  )
  set par(justify: false, leading: 0.58em, spacing: 0.9em)
  set heading(numbering: "1.1")
  show heading: set text(fill: ink, weight: "bold")
  show heading: it => {
    let offset = it.level - meta.chapter-level
    let size = if offset <= 0 { 1.65em } else if offset == 1 { 1.25em } else { 1.05em }
    block(above: if offset <= 0 { 0pt } else { 1.4em }, below: 0.7em, sticky: true, {
      set text(size: size)
      it
    })
  }
  show outline.entry.where(level: 1): set block(above: 0.7em)
  show outline.entry.where(level: 1): set text(weight: "bold")
  show link: set text(fill: accent)
  show raw: set text(font: "DejaVu Sans Mono", size: 0.84em)
  show raw.where(block: true): it => block(
    width: 100%, fill: luma(246), inset: 9pt, radius: 2pt, it,
  )
  show quote.where(block: true): it => block(
    width: 100%, fill: pale, stroke: (left: 2pt + accent),
    inset: 10pt, it.body,
  )
  set table(
    fill: (_, y) => if y == 0 { accent } else if calc.odd(y) { pale },
    stroke: none, inset: (x: 7pt, y: 5pt), align: left,
  )
  show table.cell.where(y: 0): set text(fill: white, weight: "bold")
  show table: it => {
    set par(justify: false)
    show raw.where(block: false): code => {
      show regex("[._/]"): mark => [#mark.text#sym.zws]
      code
    }
    it
  }
  set footnote.entry(separator: line(length: 25%, stroke: rule))
  show: it => if meta.lang == "fr" { french-spacing(it) } else { it }

  if meta.cover {
    page(header: none, footer: none, {
      v(1fr)
      title-block(meta)
      v(2fr)
    })
  } else {
    title-block(meta)
  }
  if meta.toc {
    outline(title: labels.at(meta.lang).contents, depth: meta.toc-depth)
  }
  body
}

#let chapter(meta, body) = {
  // Keep the first chapter with the title block unless a cover or outline precedes it.
  if not meta.first or meta.document.cover or meta.document.toc {
    pagebreak(weak: true)
  }
  if meta.part != none {
    heading(level: meta.chapter-level - 1, meta.part)
  } else {
    context {
      let part = current-part(meta)
      if part != none {
        block(below: 0.8em, sticky: true, text(size: 0.85em, fill: accent, part))
      }
    }
  }
  [#metadata(meta.source) <typoprint-source>]
  if not meta.title-in-body {
    heading(level: meta.chapter-level, meta.title)
    byline(meta, muted: muted)
  }
  body
}

#let diagram(body) = layout(size => {
  let natural = measure(body)
  let factor = calc.min(1, size.width / natural.width, 175mm / natural.height)
  assert(factor >= 0.5, message: "Diagramme trop dense pour ce gabarit : simplifier le diagramme.")
  align(center, scale(x: factor * 100%, y: factor * 100%, reflow: true, body))
})
