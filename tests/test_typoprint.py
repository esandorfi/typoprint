"""Observable contracts using real Typst, fictional content, and temporary files."""

import io
import json
import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError
from pypdf import PdfReader
from specimen import specimen

from typoprint import (
    Chapter,
    ConfigurationError,
    Document,
    RenderError,
    RenderResult,
    RuleError,
    Settings,
    load_settings,
    plan_files,
    render,
    render_files,
    write_pdf,
)
from typoprint.rendering import inspect_document

DOT = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
    "0000000c49444154789c63f8cfc0000003010100c9fe92ef0000000049454e44ae426082"
)


def pdf_text(result: RenderResult) -> str:
    return "\n".join(
        page.extract_text() for page in PdfReader(io.BytesIO(result.content)).pages
    )


class TemporaryCase(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def cli(self, *arguments, input=None):
        return subprocess.run(
            [sys.executable, "-m", "typoprint", *map(str, arguments)],
            input=input,
            capture_output=True,
            cwd=self.root,
            check=False,
        )


class RenderingTests(TemporaryCase):
    def test_real_bilingual_specimen_preserves_content_in_both_layouts(self):
        document = specimen()
        for template in ("editorial", "report"):
            for lang, paper in (("fr", "a4"), ("en", "us-letter")):
                with self.subTest(template=template, lang=lang):
                    settings = Settings(
                        template=template, lang=lang, paper=paper, cover=True
                    )
                    result = render(document, settings=settings)
                    self.assertEqual(result.warnings, ())
                    self.assertEqual(result, render(document, settings=settings))
                    text = pdf_text(result)
                    for expected in (
                        "atelier fictif",
                        "Measurements and limits",
                        "code",
                        "Note fictive",
                        "(p.",
                    ):
                        self.assertIn(expected, text)
                    reader = PdfReader(io.BytesIO(result.content))
                    self.assertIsNotNone(reader.trailer["/Root"].get("/StructTreeRoot"))
                    self.assertNotIn("/CreationDate", reader.metadata)
                    self.assertGreater(len(reader.pages), 2)
                    expected_width = 595.3 if paper == "a4" else 612
                    self.assertAlmostEqual(
                        float(reader.pages[0].mediabox.width), expected_width, delta=1
                    )

    def test_markdown_primitives_images_and_mermaid_are_real_content(self):
        source = (
            "# Fictional\n\n**Bold** and *italic*.\n\n"
            "| Policy | Value |\n|---|---|\n| Bounded | 7 |\n\n"
            "```python\nx = 1\n```\n\n![Dot](img/dot.png)\n\n"
            "```mermaid\nflowchart LR\n A[Start] --> B[Finish]\n```\n\n"
            "A note.[^n]\n\n[^n]: Footnote text.\n"
        )
        result = render(source, assets={"img/dot.png": DOT})
        text = pdf_text(result)
        for expected in ("Bounded", "x = 1", "Start", "Finish", "Footnote text"):
            self.assertIn(expected, text)
        self.assertNotIn("flowchart LR", text)
        reader = PdfReader(io.BytesIO(result.content))
        self.assertTrue(
            any(
                item.get_object().get("/Subtype") == "/Image"
                for page in reader.pages
                for item in page["/Resources"].get("/XObject", {}).values()
            )
        )

    def test_relative_assets_follow_each_chapter_name(self):
        document = Document(
            chapters=(Chapter(name="notes/page.md", markdown="![Dot](../dot.png)"),)
        )
        self.assertTrue(
            render(document, assets={"dot.png": DOT}).content.startswith(b"%PDF-")
        )

    def test_missing_and_remote_memory_assets_fail(self):
        for image in ("missing.png", "https://example.org/dot.png", "../outside.png"):
            with self.subTest(image=image), self.assertRaises(RenderError):
                render(f"![Dot]({image})")

    def test_asset_keys_cannot_escape_or_name_host_paths(self):
        for name in (
            "../escape.png",
            "/escape.png",
            "C:/escape.png",
            "a\\b.png",
            "a/../b.png",
            "./x.png",
        ):
            with self.subTest(name=name), self.assertRaises(RenderError):
                render("# Test", assets={name: DOT})

    def test_file_images_are_bounded_and_sources_unchanged(self):
        path = self.write("docs/page.md", "# Test\n\n![Dot](img/dot.png)")
        (path.parent / "img").mkdir()
        (path.parent / "img/dot.png").write_bytes(DOT)
        before = path.read_bytes()
        self.assertTrue(render_files([path]).content.startswith(b"%PDF-"))
        self.assertEqual(path.read_bytes(), before)
        (self.root / "private.png").write_bytes(DOT)
        for target in ("../private.png", "https://example.org/dot.png"):
            path.write_text(f"![Forbidden]({target})", encoding="utf-8")
            with self.assertRaises(RenderError):
                render_files([path])

    def test_linked_asset_directory_cannot_escape_the_source_root(self):
        source = self.write("docs/page.md", "# Test\n\n![Dot](assets/dot.png)")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "dot.png").write_bytes(DOT)
        link = source.parent / "assets"
        if os.name == "nt":
            # Junctions do not require Windows' symbolic-link privilege.
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RenderError, "escapes the render root"):
            render_files([source])
        self.assertEqual((outside / "dot.png").read_bytes(), DOT)

    def test_html_images_use_the_same_bounded_asset_snapshot(self):
        path = self.write("docs/page.md", '<img src="dot.png" alt="Dot">')
        (path.parent / "dot.png").write_bytes(DOT)
        self.assertTrue(render_files([path]).content.startswith(b"%PDF-"))

    def test_inline_typst_and_front_matter_cannot_select_executable_options(self):
        source = (
            "---\ntemplate: missing\ncover: true\nlang: zz\nchapter-level: 99\n"
            "source: SECRET_SENTINEL\nprint-context: private\n---\n# Fictional\n\n"
            '<!--raw-typst #panic("EXECUTED")-->\n'
        )
        result = render(source)
        self.assertNotIn("SECRET_SENTINEL", pdf_text(result))
        resolved = inspect_document(
            Document(chapters=(Chapter(markdown=source),)), Settings()
        )
        self.assertEqual(
            (resolved["template"], resolved["cover"], resolved["lang"]),
            ("editorial", False, "fr"),
        )

    def test_invalid_mermaid_fails_without_code_fallback(self):
        with self.assertRaises(RenderError):
            render("```mermaid\nthis is not a diagram\n```")

    def test_html_and_missing_anchors_remain_printable(self):
        result = render(
            '# Anchors\n\n<a id="target"></a>\n\n## Target\n\n'
            'An [ambiguous](#target), <a href="#target">HTML link</a>, '
            "a [missing](#missing), and [valid](#anchors)."
        )
        self.assertIn("missing", pdf_text(result))

    def test_internal_links_and_published_fallback(self):
        first = self.write(
            "docs/start.md",
            "# Start\n\nSee [other](other.md#details) and [code](../src/app.py).",
        )
        second = self.write(
            "docs/other.md", "# Other\n\n## Details\n\nBack [home](start.md)."
        )
        with patch("pathlib.Path.cwd", return_value=self.root):
            result = render_files(
                [first, second], settings=Settings(link_base="https://example.org/repo")
            )
        text = pdf_text(result)
        self.assertIn("(p.", text)
        reader = PdfReader(io.BytesIO(result.content))
        links = [
            annotation.get_object()
            for page in reader.pages
            for annotation in page.get("/Annots", [])
        ]
        self.assertTrue(
            any(
                link.get("/A", {}).get("/URI") == "https://example.org/repo/src/app.py"
                for link in links
            )
        )

    def test_concurrent_calls_keep_settings_and_documents_separate(self):
        def run(index):
            return render(
                f"# Body {index}\n\nPrivate text {index}",
                settings=Settings(title=f"Title {index}", cover=True),
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(run, range(4)))
        for index, result in enumerate(results):
            self.assertEqual(result, run(index))
            text = pdf_text(result)
            self.assertIn(f"Private text {index}", text)
            for other in range(4):
                if other != index:
                    self.assertNotIn(f"Private text {other}", text)

    def test_duplicate_chapters_and_invalid_settings_fail_at_boundary(self):
        with self.assertRaises(ValidationError):
            Document(chapters=(Chapter(markdown="a"), Chapter(markdown="b")))
        with self.assertRaises(ValidationError):
            Settings.model_validate({"toc_depth": 9})
        with self.assertRaises(ValidationError):
            Chapter(name="../private.md", markdown="x")


class ExtensionTests(TemporaryCase):
    def test_transforms_precede_validation_for_every_chapter(self):
        calls = []

        def first(markdown):
            calls.append("first")
            return markdown.replace("TOKEN", "changed")

        def second(markdown):
            calls.append("second")
            return markdown + "\n\nAfterwards."

        def validate(markdown):
            calls.append("validate")
            self.assertNotIn("TOKEN", markdown)
            self.assertIn("Afterwards", markdown)

        document = Document(
            chapters=(
                Chapter(name="a.md", markdown="# A\nTOKEN"),
                Chapter(name="b.md", markdown="# B\nTOKEN"),
            )
        )
        result = render(document, transforms=[first, second], validators=[validate])
        self.assertEqual(calls, ["first", "second", "validate"] * 2)
        self.assertEqual(pdf_text(result).count("changed"), 2)
        self.assertIn("TOKEN", document.chapters[0].markdown)

    def test_rule_refusal_stops_before_compilation_and_does_not_publish(self):
        path = self.write("source.md", "# Fictional\n\nTOKEN")

        def refuse(markdown):
            raise RuleError("Required section missing")

        with patch("typoprint.rendering._compile") as compiler:
            with self.assertRaisesRegex(RuleError, "Required section"):
                render_files([path], validators=[refuse])
            compiler.assert_not_called()
        self.assertIn("TOKEN", path.read_text(encoding="utf-8"))

    def test_callback_errors_do_not_copy_source_into_error_message(self):
        def broken(markdown):
            raise RuntimeError(markdown)

        with self.assertRaises(RuleError) as caught:
            render("SECRET_SENTINEL", transforms=[broken])
        self.assertNotIn("SECRET_SENTINEL", str(caught.exception))
        with self.assertRaises(RuleError):
            render("# Test", transforms=[lambda markdown: None])

    def test_custom_template_extends_builtin_and_receives_options(self):
        self.write(
            "bundle/template.typ",
            """#import "@local/typoprint:0.1.0": editorial
#let document(meta, body) = editorial.document(meta, [#meta.template_options.at("banner") #body])
#let chapter = editorial.chapter
#let diagram = editorial.diagram
""",
        )
        settings = Settings(
            template=str(self.root / "bundle"),
            template_options={"banner": "CUSTOM_BANNER"},
        )
        result = render("# Fictional\n\nText", settings=settings)
        self.assertIn("CUSTOM_BANNER", pdf_text(result))
        self.assertEqual(result, render("# Fictional\n\nText", settings=settings))

    def test_template_contract_and_missing_bundle_errors(self):
        with self.assertRaises(ConfigurationError):
            render(
                "# Fictional", settings=Settings(template=str(self.root / "missing"))
            )
        self.write("bundle/template.typ", "#let document(meta, body) = body\n")
        with self.assertRaisesRegex(RenderError, "export chapter"):
            render("# Fictional", settings=Settings(template=str(self.root / "bundle")))


class PlanningTests(TemporaryCase):
    def test_directory_order_exclusions_and_explicit_file_priority(self):
        for name in (
            "docs/README.md",
            "docs/chapter-10.md",
            "docs/chapter-2.md",
            "docs/sub/README.md",
            "docs/sub/deep/page.md",
            "docs/skip/idea.md",
        ):
            self.write(name, f"# {Path(name).stem}\n")
        plan = plan_files(
            [self.root / "docs"],
            recursive=True,
            exclude=["skip", "**/deep"],
            by_folder=True,
        )
        self.assertEqual(
            [entry.path.relative_to(plan.root).as_posix() for entry in plan.files],
            ["README.md", "chapter-2.md", "chapter-10.md", "sub/README.md"],
        )
        self.assertEqual(
            [entry.part for entry in plan.files], ["docs", None, None, "sub"]
        )
        explicit = self.root / "docs/skip/idea.md"
        self.assertEqual(
            plan_files([explicit], exclude=["**/*.md"]).files[0].path, explicit
        )
        self.assertIn("chapter-2", pdf_text(render_files(plan)))

    def test_contents_map_orders_parts_and_unplaced_pages(self):
        toc = self.write(
            "book/README.md",
            "# Book\n\n[ignored](loose.md)\n\n## First\n\n| Read | Next |\n|---|---|\n| [B](b/b.md) | [A](a/) |\n\n```text\n[ignore](loose.md)\n```\n\n## Second\n\n[B folder](b/) [up](../other.md)\n",
        )
        for name in (
            "a/chapter-10.md",
            "a/chapter-2.md",
            "b/b.md",
            "b/z.md",
            "loose.md",
        ):
            self.write("book/" + name, f"# {Path(name).stem}\n")
        plan = plan_files(order=toc, lang="en")
        self.assertEqual(
            [entry.path.relative_to(plan.root).as_posix() for entry in plan.files],
            [
                "README.md",
                "b/b.md",
                "a/chapter-2.md",
                "a/chapter-10.md",
                "b/z.md",
                "loose.md",
            ],
        )
        self.assertEqual(
            [entry.part for entry in plan.files],
            [None, "First", None, None, "Second", "Other pages"],
        )
        self.assertEqual(len(plan.warnings), 1)
        with self.assertRaises(RenderError):
            plan_files(order=toc, strict=True)
        self.assertFalse(
            plan_files(order=toc, strict=True, exclude=["loose.md"]).warnings
        )
        self.assertNotIn(
            "README.md",
            [
                entry.path.name
                for entry in plan_files(order=toc, exclude=["README.md"]).files
            ],
        )

    def test_missing_wrong_case_and_invalid_utf8_are_diagnosed(self):
        toc = self.write("book/README.md", "## Guides\n\n[Guide](GUIDE.md)")
        self.write("book/guide.md", "# Guide")
        with self.assertRaises(RenderError):
            plan_files(order=toc)
        invalid = self.root / "bad.md"
        invalid.write_bytes(b"line\n\xff\n")
        with self.assertRaisesRegex(RenderError, r":2: invalid UTF-8"):
            plan_files([invalid])
        with self.assertRaises(RenderError):
            plan_files([self.root / "absent.md"])

    def test_bom_and_non_heading_title_fallback(self):
        path = self.root / "page.md"
        path.write_bytes(b"\xef\xbb\xbf---\ntitle: From front matter\n---\n\nBody")
        self.assertIn("From front matter", pdf_text(render_files([path])))
        self.assertIn("page", pdf_text(render_files([self.write("page.md", "Body")])))

    def test_invalid_planning_combinations_are_refused(self):
        path = self.write("page.md", "# Page")
        for kwargs in (
            {"paths": [path], "order": path},
            {"paths": [path], "strict": True},
            {"paths": [path, path]},
            {},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(RenderError):
                plan_files(**kwargs)


class ConfigAndCliTests(TemporaryCase):
    def test_defaults_preset_overrides_and_front_matter(self):
        config = self.write(
            "typoprint.toml",
            '[defaults]\ncover = true\ntoc = true\nauthor = "Defaults"\n[presets.short]\ncover = false\ntoc = false\ntitle = "Preset"\n',
        )
        settings = load_settings(config, preset="short")
        source = (
            "---\ntitle: Front\nauthor: Front author\ndate: 2026-10-01\n---\n# Body"
        )
        result = render(source, settings=settings, overrides=Settings(title="Explicit"))
        reader = PdfReader(io.BytesIO(result.content))
        self.assertEqual(reader.metadata.title, "Explicit")
        self.assertEqual(reader.metadata.author, "Defaults")
        self.assertFalse(settings.cover)
        self.assertFalse(settings.toc)
        self.assertIn("2026-10-01", pdf_text(result))

    def test_unknown_config_presets_settings_and_paths(self):
        for text in (
            "unknown = true\n",
            '[defaults]\ncolour = "red"',
            '[defaults]\ncover = "maybe"',
            "[defaults",
        ):
            path = self.write("bad.toml", text)
            with self.subTest(text=text), self.assertRaises(ConfigurationError):
                load_settings(path)
        path = self.write("valid.toml", "[defaults]\n")
        with self.assertRaises(ConfigurationError):
            load_settings(path, preset="missing")
        with self.assertRaises(ConfigurationError):
            load_settings(self.root / "missing.toml")

    def test_config_resource_paths_belong_to_the_file(self):
        config = self.write(
            "project/typoprint.toml",
            '[defaults]\ntemplate = "templates/acme"\nfont_paths = ["fonts"]\n[presets.report]\ntemplate = "report"\n',
        )
        settings = load_settings(config)
        self.assertEqual(settings.template, str(self.root / "project/templates/acme"))
        self.assertEqual(settings.font_paths, (self.root / "project/fonts",))
        self.assertEqual(load_settings(config, preset="report").template, "report")

    def test_cli_automatically_loads_only_working_directory_config(self):
        path = self.write("page.md", "# Body")
        self.write(
            "typoprint.toml",
            '[defaults]\ntitle = "Config title"\ncover = true\n[presets.short]\ncover = false\n',
        )
        result = self.cli(
            path, "--preset", "short", "--no-toc", "--title", "CLI title", "--dry-run"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["settings"]["title"], "CLI title")
        self.assertFalse(payload["settings"]["cover"])
        self.assertFalse(payload["settings"]["toc"])
        self.assertEqual(payload["files"], [{"name": "page.md", "part": None}])
        ignored = self.cli(path, "--no-config", "--dry-run")
        self.assertEqual(json.loads(ignored.stdout)["settings"]["title"], "Body")
        self.assertFalse(list(self.root.glob("*.pdf")))

    def test_library_does_not_discover_configuration(self):
        self.write("typoprint.toml", '[defaults]\ntitle = "UNWANTED"\n')
        with patch("pathlib.Path.cwd", return_value=self.root):
            result = render("# Desired")
        self.assertEqual(
            PdfReader(io.BytesIO(result.content)).metadata.title, "Desired"
        )

    def test_dry_run_resolves_metadata_without_rendering_diagrams_or_images(self):
        path = self.write(
            "page.md",
            "---\nauthor: Author\n---\n# **Rich** title\n\n![Missing](absent.png)\n\n```mermaid\ninvalid diagram\n```",
        )
        result = self.cli(path, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["settings"]["title"], "Rich title")
        self.assertEqual(payload["settings"]["author"], "Author")

    def test_utf8_stdin_binary_stdout_and_module_entrypoint(self):
        result = self.cli("-", "-o", "-", input="# Français\n\nÉquipe fictive".encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(b"%PDF-"))
        self.assertIn("Équipe fictive", pdf_text(RenderResult(content=result.stdout)))
        self.assertEqual(result.stderr, b"")
        self.assertEqual(self.cli("--version").stdout.strip(), b"0.1.0")

    def test_cli_output_matches_library_and_input_overwrite_is_refused(self):
        path = self.write("page.md", "# Fictional\n\nBody")
        output = self.root / "output.pdf"
        result = self.cli(path, "-o", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(output.read_bytes(), render_files([path]).content)
        refused = self.cli(path, "-o", path)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(path.read_text(encoding="utf-8"), "# Fictional\n\nBody")

    def test_cli_errors_preserve_destination_and_do_not_pollute_stdout(self):
        path = self.write("bad.md", "```mermaid\ninvalid diagram\n```")
        output = self.root / "existing.pdf"
        output.write_bytes(b"PREVIOUS")
        result = self.cli(path, "-o", output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(output.read_bytes(), b"PREVIOUS")
        for args in (
            ("-", path),
            (path, "--strict"),
            (path, "--preset", "absent"),
            (path, "--meta", "colour=red"),
            (path, "--meta", "title=A", "--title", "B"),
            (path, "--template-option", "key=invalid"),
        ):
            with self.subTest(args=args):
                self.assertEqual(self.cli(*args).returncode, 2)


class AtomicOutputTests(TemporaryCase):
    def test_failed_replace_preserves_old_pdf_and_cleans_temporary_file(self):
        destination = self.root / "document.pdf"
        destination.write_bytes(b"PREVIOUS")
        with patch(
            "typoprint.output.os.replace", side_effect=OSError("injected failure")
        ):
            with self.assertRaises(RenderError):
                write_pdf(RenderResult(content=b"NEW"), destination)
        self.assertEqual(destination.read_bytes(), b"PREVIOUS")
        self.assertEqual(list(self.root.glob(".typoprint-*")), [])
        self.assertEqual(
            write_pdf(RenderResult(content=b"COMPLETE"), destination), destination
        )
        self.assertEqual(destination.read_bytes(), b"COMPLETE")


if __name__ == "__main__":
    unittest.main()
