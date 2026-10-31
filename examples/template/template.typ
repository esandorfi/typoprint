// A trusted local bundle extending the bundled editorial layout.
#import "@local/typoprint:0.1.0": editorial

#let document(meta, body) = {
  show strong: set text(fill: rgb(meta.template_options.at("accent", default: "#165d8d")))
  editorial.document(meta, body)
}
#let chapter = editorial.chapter
#let diagram = editorial.diagram
