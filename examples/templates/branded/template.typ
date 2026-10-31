// A branded layout: bundle-local module and logo, a custom cover, and options.
// Options: company (default "Acme"), accent (default "#0b6e4f").
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
