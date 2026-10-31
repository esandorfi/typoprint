// Mermaid belongs to the content pipeline; the layout owns figure dimensions.
#import "@preview/merman:0.5.0": mermaid-result

#let check-svg(nodes) = {
  for node in nodes {
    if type(node) == dictionary {
      assert(not (node.tag in ("script", "foreignObject", "image")),
        message: "Mermaid : contenu SVG externe ou actif refusé.")
      for (key, value) in node.attrs {
        assert(not key.starts-with("on"), message: "Mermaid : attribut actif refusé.")
        if key == "href" or key.ends-with(":href") {
          assert(value.starts-with("#"), message: "Mermaid : ressource externe refusée.")
        }
      }
      check-svg(node.children)
    }
  }
}

#let diagram-svg(source) = {
  let result = mermaid-result(source, site-config: (
    layout: "dagre", theme: "default", look: "classic",
    securityLevel: "strict", htmlLabels: false,
  ))
  assert(result.ok, message: "Diagramme Mermaid invalide ou non pris en charge.")
  let data = bytes(result.svg)
  check-svg(xml(data))
  data
}

#let render-code(template, body, block: false, lang: none, ..args) = {
  if block and lang == "mermaid" {
    template.diagram(image(diagram-svg(body), format: "svg", alt: "Diagramme Mermaid"))
  } else {
    raw(body, block: block, lang: lang, ..args)
  }
}
