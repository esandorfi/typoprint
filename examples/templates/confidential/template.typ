// Extends the bundled `report` layout with a diagonal watermark.
// Options: label (default "CONFIDENTIAL"), accent (default "#b3261e").
#import "@local/typoprint:0.1.0": report

#let document(meta, body) = {
  let options = meta.template_options
  let label = options.at("label", default: "CONFIDENTIAL")
  let tint = rgb(options.at("accent", default: "#b3261e")).transparentize(88%)
  // `report.document` does not set `page.background`, so this survives it.
  set page(background: rotate(-30deg, text(size: 72pt, weight: "bold", fill: tint, label)))
  report.document(meta, body)
}
#let chapter = report.chapter
#let diagram = report.diagram
