# Verification

The regression suite uses fictional temporary documents and the real Typst
compiler. It checks rendering content, layouts, image roots, Mermaid, links,
metadata, configuration precedence, custom templates, callbacks, concurrency,
atomic output failure, and CLI subprocesses.

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv build
```

`uv build` produces a wheel and source archive in `dist/`. Both contain the
bundled packages, WASM plugins, fonts, and their complete notices. The source
archive also contains tests, examples, documentation, and verification tooling.

## Clean-wheel smoke test

Install the built wheel into a new environment with no editable checkout. After
preparing dependency wheels, the installation and render can run offline:

```bash
uv venv .cache/wheel-smoke
uv run --no-project --python .cache/wheel-smoke/bin/python --with pip python -m pip download --dest .cache/wheelhouse dist/typoprint-0.1.0-py3-none-any.whl
uv pip install --offline --no-index --find-links .cache/wheelhouse --python .cache/wheel-smoke/bin/python dist/typoprint-0.1.0-py3-none-any.whl
.cache/wheel-smoke/bin/python tools/wheel_smoke.py
```

On Windows, use `.cache/wheel-smoke/Scripts/python.exe`. The script checks its
import location, renders both layouts and Mermaid, checks repeatable bytes, tests
stdin/stdout and a custom template, and prints PDF SHA-256 values. It requires
only runtime dependencies. Rendering does not depend on the checkout directory.

## Linux without network

Prepare dependency wheels while network is available, then install and render in
a disposable container with networking disabled:

```bash
docker run --rm -v "$PWD:/work" python:3.13-slim sh -c \
  'python -m pip download --dest /work/.cache/linux-wheelhouse /work/dist/*.whl'
docker run --rm --network none -v "$PWD:/work:ro" python:3.13-slim sh -c \
  'python -m venv /tmp/smoke && /tmp/smoke/bin/pip install --no-index --find-links /work/.cache/linux-wheelhouse /work/dist/*.whl && cd /tmp && /tmp/smoke/bin/python /work/tools/wheel_smoke.py'
```

These examples use a POSIX shell. In PowerShell, use an absolute Windows bind path
instead of `$PWD` interpolation and quote the container command as one argument.
The container is removed automatically. The repository is read-only during the
offline render; outputs and environments live under `/tmp`.

The CI matrix runs checks and clean-wheel smoke tests on Windows, Ubuntu, and
macOS, with Python 3.13 and 3.14. Ubuntu additionally renders in a network-disabled
container. No workflow publishes a package or provisions a service.

PDF hashes are compared within one pinned environment. When assessing portability,
compare smoke-test hashes between hosts as additional evidence rather than making
unqualified promises across future compiler or font updates. Custom extensions
are responsible for their own determinism and offline dependencies.
