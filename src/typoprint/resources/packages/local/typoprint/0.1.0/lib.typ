// Shared content pipeline of the packaged print templates.
// Each template module exports `document(meta, body)` and `chapter(meta, body)`;
// neither depends on cmarker, so another Markdown reader can produce the same calls.
#import "@preview/cmarker:0.1.10"
#import "editorial.typ"
#import "report.typ"
#import "diagrams.typ": render-code

#import "foundations.typ"
#let templates = (editorial: editorial, report: report)

// An in-file anchor that is missing or ambiguous (an `<a id>` repeating a heading
// slug) prints as plain text instead of aborting the whole document.
#let anchor-link(target, ..args) = if type(target) == label {
  context if query(target).len() == 1 { link(target, ..args) } else {
    args.pos().at(0, default: none)
  }
} else { link(target, ..args) }

// Path segments without `.`, `..` folded; a leading `..` means the path climbs out.
#let normalize(segments) = segments.fold((), (kept, segment) => {
  if segment == "" or segment == "." { kept } else if segment == ".." and kept.len() > 0 and kept.last() != ".." {
    kept.slice(0, -1)
  } else { kept + (segment,) }
})

#let chapter-label(index) = label("typoprint-chapter-" + str(index))

// A local link resolves against its file, as on GitHub. A printed file is reached in
// the PDF, with its page when it is another chapter; another file opens at
// `link-base` when given; otherwise only the text prints.
#let resolve-link(chapters, current, dir, base-dir, link-base) = (target, ..args) => {
  let body = args.pos().at(0, default: none)
  if type(target) == label or target.contains(regex("^[A-Za-z][A-Za-z0-9+.-]*:")) {
    return anchor-link(target, ..args)
  }
  let (path, ..rest) = target.split("#")
  let fragment = if rest.len() > 0 { rest.join("#") } else { "" }
  let segments = path.split("/")
  let from-root = if path.starts-with("/") { segments } else { dir.split("/") + segments }
  let relative = normalize(from-root)
  let index = if relative.len() > 0 and relative.first() != ".." {
    chapters.at("/" + relative.join("/"), default: none)
  }
  if index != none {
    let anchor = label("d" + str(index) + "-" + fragment)
    context {
      let destination = if fragment != "" and query(anchor).len() == 1 { anchor } else {
        chapter-label(index)
      }
      if index == current { link(destination, body) } else {
        let number = counter(page).at(locate(destination)).first()
        link(destination, [#body~(p.~#number)])
      }
    }
  } else if link-base != none and path != "" {
    let published = normalize(base-dir.split("/") + from-root)
    if published.len() > 0 and published.first() != ".." {
      let address = link-base + published.join("/") + if fragment != "" { "#" + fragment } else { "" }
      link(address, body)
    } else { body }
  } else if path == "" { anchor-link(target, ..args) } else { body }
}

// Front matter values print as text: `version: 2` gives "2", a list of names joins.
#let as-text(value) = if value == none or type(value) == str { value } else if type(value) == array {
  value.map(as-text).join(", ")
} else { repr(value) }

// Only these front-matter values may become document metadata.
#let document-meta(settings, first, count, chapter-level) = {
  let field(key) = if settings.at(key) != none { settings.at(key) } else {
    as-text(first.front.at(key, default: none))
  }
  (
    ..settings,
    title: if settings.title != none { settings.title } else { first.meta.title },
    subtitle: field("subtitle"), author: field("author"),
    date: field("date"), version: field("version"),
    toc: if settings.toc != none { settings.toc } else { count > 1 },
    toc-depth: settings.toc_depth,
    cover: settings.cover,
    chapter-level: chapter-level,
  )
}

#let plain-title(body) = {
  let fields = body.fields()
  if "text" in fields { fields.text } else if "children" in fields {
    fields.children.map(plain-title).join("")
  } else if "body" in fields { plain-title(fields.body) } else { " " }
}

// Resolve metadata for inspection without loading images, diagrams, or user layouts.
#let inspect-inputs() = {
  let options = json(bytes(sys.inputs.options))
  let first = options.files.first()
  let (front, body) = cmarker.render-with-metadata(
    first.text.trim("\u{FEFF}", at: start, repeat: false),
    raw-typst: false, metadata-block: "frontmatter-yaml",
    scope: (image: (source, ..args) => args.named().at("alt", default: "")),
  )
  let front = if type(front) == dictionary { front } else { (:) }
  let children = if body.func() == [].func() { body.children } else { (body,) }
  let opening = children.find(child => child.func() == heading and child.depth == 1)
  let declared = front.at("title", default: none)
  let title = if declared != none { as-text(declared) } else if opening != none {
    // Content titles retain formatting in print; the inspection uses plain text.
    plain-title(opening.body)
  } else { first.stem }
  let level = if options.files.any(file => file.part != none) { 2 } else { 1 }
  document-meta(options.settings, (front: front, meta: (title: title)), options.files.len(), level)
}


// Discover image references without reading assets or invoking user layouts.
#let inspect-assets() = {
  let options = json(bytes(sys.inputs.options))
  for file in options.files {
    let (_, body) = cmarker.render-with-metadata(
      file.text.trim("\u{FEFF}", at: start, repeat: false),
      raw-typst: false, metadata-block: "frontmatter-yaml",
      scope: (
        image: (source, ..args) => [#metadata((source: source, dir: file.dir)) <typoprint-asset>],
        raw: (body, ..args) => [],
        link: (target, ..args) => args.pos().at(0, default: none),
        heading: (body, ..args) => body,
      ),
      html: (a: (attrs, body) => body),
    )
    body
  }
}

// `load` and `picture` come from the root file: `read` and `image` resolve paths
// relative to the file that calls them, and only the root file sees the inputs.
#let print-documents(load, picture) = {
  let options = json(bytes(sys.inputs.options))
  let settings = options.settings
  let template = if settings.template in templates { templates.at(settings.template) } else {
    import "@local/typoprint-custom:0.1.0" as custom
    custom
  }
  for key in ("document", "chapter", "diagram") {
    assert(key in template, message: "Template must export " + key)
  }
  // With parts (folders or groups), parts take level 1 and every Markdown heading
  // moves one level down. Python decides which file opens which part.
  let chapter-level = if options.files.any(file => file.part != none) { 2 } else { 1 }
  // Printed files by path, for links between them.
  let printed = (:)
  for (index, file) in options.files.enumerate() {
    printed.insert(file.path, index)
  }
  let chapters = options.files.enumerate().map(((index, file)) => {
    let follow = resolve-link(printed, index, file.dir, options.at("base-dir"), settings.link_base)
    let resolve(source) = {
      assert(
        not source.contains("://"),
        message: "image distante refusée : " + source + " ; copier l’image sous la racine de rendu",
      )
      if source.starts-with("/") { source } else if file.dir == "" { "/" + source } else {
        "/" + file.dir + "/" + source
      }
    }
    let prefix = "d" + str(index) + "-"
    let (front, body) = cmarker.render-with-metadata(
      // A byte order mark would hide the front matter.
      (if "text" in file { file.text } else { load(file.path) }).trim("\u{FEFF}", at: start, repeat: false),
      // Markdown is data: comments never run Typst code or import packages.
      raw-typst: false,
      h1-level: chapter-level,
      label-prefix: prefix,
      metadata-block: "frontmatter-yaml",
      html: (
        // `<a id="…"></a>` is a common Markdown anchor: only `href` makes a link.
        a: (attrs, body) => {
          let target = attrs.at("href", default: none)
          let shown = if target == none { body } else if target.starts-with("#") {
            anchor-link(label(prefix + target.slice(1)), body)
          } else { follow(target, body) }
          if "id" in attrs { [#shown#metadata(none)#label(prefix + attrs.id)] } else {
            shown
          }
        },
      ),
      scope: (
        raw: render-code.with(template),
        link: follow,
        image: (source, ..args) => picture(if type(source) == str { resolve(source) } else { source }, ..args),
      ),
    )
    let front = if type(front) == dictionary { front } else { (:) }
    let children = if body.func() == [].func() { body.children } else { (body,) }
    let opening = children.find(child => (
      child.func() == heading and child.depth == chapter-level
    ))
    let declared = front.at("title", default: none)
    let title = if declared != none { [#declared] } else if opening != none { opening.body } else {
      [#file.stem]
    }
    (
      meta: (
        ..settings,
        // A chapter shows its own date and version, never the document's.
        date: front.at("date", default: none),
        version: front.at("version", default: none),
        title: title,
        title-in-body: declared == none and opening != none,
        chapter-level: chapter-level,
        part: file.part,
        source: file.source,
      ),
      front: front,
      // Links to this file land here, after the template's page break.
      body: [#metadata(none)#chapter-label(index)] + body,
    )
  })
  let meta = document-meta(settings, chapters.first(), chapters.len(), chapter-level)
  show: template.document.with(meta)
  for (index, chapter) in chapters.enumerate() {
    template.chapter((..chapter.meta, first: index == 0, document: meta), chapter.body)
  }
}

