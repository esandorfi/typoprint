"""Run from a clean environment with the built wheel installed, not the checkout."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import typoprint
from typoprint import (
    Chapter,
    Document,
    RuleError,
    Settings,
    render,
    render_files,
    write_pdf,
)


def main() -> None:
    installed = Path(typoprint.__file__).resolve()
    if "site-packages" not in installed.parts:
        raise RuntimeError(
            f"Smoke test imported a checkout instead of the wheel: {installed}"
        )
    markdown = (
        '---\ntitle: "Fictional workshop"\nauthor: "Fictional team"\n---\n'
        "## Results\n\nA **bounded** policy. Une mesure : « vérifier ».\n\n"
        "| Policy | Limit |\n|---|---|\n| Bounded | 7 |\n\n"
        "```python\nx = 1\n```\n\n"
        "```mermaid\nflowchart LR\n A[Start] --> B[Finish]\n```\n\n"
        "A note.[^n]\n\n[^n]: Fictional footnote.\n"
    )
    document = Document(
        chapters=(
            Chapter(name="workshop.md", markdown=markdown),
            Chapter(
                name="results.md",
                markdown="# Results\n\nSee [workshop](workshop.md#results).",
            ),
        )
    )
    hashes = {}
    with TemporaryDirectory(prefix="typoprint-wheel-") as temporary:
        root = Path(temporary)
        for layout in ("editorial", "report"):
            options = Settings(template=layout, cover=True)
            result = render(document, settings=options)
            if not result.content.startswith(b"%PDF-") or result.warnings:
                raise RuntimeError(
                    f"Failed {layout} wheel rendering: {result.warnings}"
                )
            if result != render(document, settings=options):
                raise RuntimeError("PDF bytes changed between identical renders")
            write_pdf(result, root / f"{layout}.pdf")
            hashes[layout] = hashlib.sha256(result.content).hexdigest()
        source = root / "fictional.md"
        source.write_text(markdown, encoding="utf-8")
        before = source.read_bytes()
        render_files([source])
        if source.read_bytes() != before:
            raise RuntimeError("Rendering modified a source")
        cli = subprocess.run(
            [sys.executable, "-m", "typoprint", "-", "-o", "-"],
            input=b"# Stdin\n\nFictional text",
            capture_output=True,
            cwd=root,
            check=True,
        )
        if not cli.stdout.startswith(b"%PDF-") or cli.stderr:
            raise RuntimeError("CLI binary output was polluted")
        bundle = root / "bundle"
        bundle.mkdir()
        (bundle / "template.typ").write_text(
            '#import "@local/typoprint:0.1.0": report\n'
            "#let document(meta, body) = report.document(meta, body)\n"
            "#let chapter = report.chapter\n#let diagram = report.diagram\n",
            encoding="utf-8",
        )
        render("# Custom", settings=Settings(template=str(bundle)))

        def validate(markdown: str) -> None:
            if "Summary" not in markdown:
                raise RuleError("Missing Summary")

        render(
            "# Summary\n\nTOKEN",
            transforms=[lambda value: value.replace("TOKEN", "Text")],
            validators=[validate],
        )
    print(json.dumps({"installed": str(installed), "sha256": hashes}, indent=2))


if __name__ == "__main__":
    main()
