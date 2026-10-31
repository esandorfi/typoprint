# Typoprint contributor instructions

Keep the library and CLI thin and share the rendering pipeline. Rendering is
synchronous, offline with bundled resources, and isolated per invocation. Never
rewrite source Markdown, execute embedded Typst from Markdown, or discover Python
plugins from TOML. Templates and explicit callbacks are trusted developer code.

Python 3.13+; use `uv sync --locked`. Runtime dependencies are Typst and Pydantic.
Changes must pass `uv run ruff format --check .`, `uv run ruff check .`,
`uv run ty check`, and `uv run pytest`. Use real temporary input files and real
Typst for behavioral tests. Keep dependency/font licenses beside bundled assets.
Update user docs with behavior changes. Build with `uv build` and verify the
installed wheel when changing resources or packaging. Do not publish automatically.
