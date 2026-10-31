# CLI behavior

Run `typoprint --help` for the complete option list, or use `python -m typoprint`.

| Input | Behavior |
| --- | --- |
| Files | Preserve argument order; duplicate selections fail |
| Folder | README first, other `.md` files in natural order |
| `--recursive` | Files of a folder precede its subfolders |
| `--by-folder` | Folder changes open parts; filenames become chapters beneath them |
| `--exclude GLOB` | Match relative files or their parent folders; repeatable |
| `--order MAP.md` | Map first, links under `##` headings define parts and chapters |
| `--strict` | With `--order`, refuse pages absent from the map |
| `-` | Read one UTF-8 Markdown document from stdin |
| `--dry-run` | JSON input order, part openings, resolved settings, and warnings |

`--order` replaces positional paths, `--recursive`, and `--by-folder`. Stdin cannot
be mixed with file discovery. Explicit files are included even if excluded by a
folder glob. Map targets match exact spelling and case on every platform. An empty
selection, missing file, invalid UTF-8, or broken map target fails before PDF output.

The contents-map parser recognizes inline links in prose, lists, and tables. It
ignores fenced and inline code, images, external URLs, anchor-only links, and links
outside the map's directory. Duplicate links keep their first position. Directory
links add remaining pages recursively. Excluded links place no pages. Reference
links and deeply nested Markdown link syntax are outside this small ordering parser.

Printed-file links resolve to the destination chapter or a known section anchor.
Links across chapters include `(p. N)` for paper readers. Missing or ambiguous
in-file anchors print as text; missing cross-file anchors fall back to the chapter.
Nonprinted relative files become text unless `--link-base URL` supplies the web
folder publishing the working directory. Its render root must lie under that
working directory. Existing HTTP(S) links remain active. For in-memory documents,
chapter names define internal links, while `link_base` is unavailable.

Metadata shortcuts are `--title`, `--subtitle`, and `--author`; `--meta KEY=VALUE`
also accepts `date` and `version`. A field supplied twice in one invocation fails.
`--template`, `--lang`, `--paper`, `--cover`/`--no-cover`, `--toc`/`--no-toc`, and
`--toc-depth` override project settings. Font paths and template options can also
be supplied explicitly. Front matter cannot select settings or executable code.

`-o PATH` writes atomically and preserves the existing destination on a render or
replacement failure. The output directory must exist. An output resolving to a
selected input is refused. Without `-o`, the first file stem or folder name supplies
the output name in the current directory; stdin uses `document.pdf`. `-o -` sends
binary PDF bytes to stdout. Successful file destinations, warnings, and errors go
to stderr; dry-run JSON goes to stdout. Success returns 0; usage, configuration,
input, and rendering failures return 2.

Dry-run parses front matter and resolves automatic choices but does not lay out
document bodies, load images, render diagrams, or execute custom layouts. It is
an input/settings inspection, not a guarantee that the eventual PDF can compile.
It performs no network requests with the supplied package set.
