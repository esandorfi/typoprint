"""Thin command-line adapter over the public library."""

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

from pydantic import ValidationError

from typoprint.config import load_settings
from typoprint.models import (
    Chapter,
    ConfigurationError,
    Document,
    Settings,
    TypoprintError,
)
from typoprint.output import write_pdf
from typoprint.planning import plan_files
from typoprint.rendering import (
    document_from_plan,
    inspect_document,
    render,
    render_files,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="typoprint",
        description=(
            "Markdown in. Beautiful PDFs out.\n"
            "Write in Markdown. Print like a publisher.\n\n"
            "Prints Markdown to PDF offline with Typst."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths", nargs="*", help="Markdown files or folders; '-' reads UTF-8 stdin"
    )
    parser.add_argument("--version", action="version", version=version("typoprint"))
    parser.add_argument(
        "-o", "--output", help="PDF destination; '-' writes binary PDF to stdout"
    )
    parser.add_argument(
        "--order", type=Path, help="Markdown contents map; ## headings define parts"
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Include subfolders"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Exclude a relative path or directory (repeatable)",
    )
    parser.add_argument(
        "--by-folder", action="store_true", help="Open a part for each folder"
    )
    parser.add_argument(
        "--strict", action="store_true", help="With --order, refuse unplaced pages"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON with input order and resolved settings, without a PDF",
    )
    config = parser.add_mutually_exclusive_group()
    config.add_argument(
        "--config",
        type=Path,
        help="Project TOML file (default: ./typoprint.toml if present)",
    )
    config.add_argument(
        "--no-config", action="store_true", help="Ignore the project configuration"
    )
    parser.add_argument("--preset", help="Named preset in the selected configuration")
    parser.add_argument(
        "--template", help="editorial, report, or a directory containing template.typ"
    )
    for name in ("title", "subtitle", "author"):
        parser.add_argument(
            f"--{name}", help=f"Document {name}; overrides front matter"
        )
    parser.add_argument(
        "--meta",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Set title, subtitle, author, date, or version (repeatable)",
    )
    parser.add_argument(
        "--lang", choices=("fr", "en"), help="Typography language (default: fr)"
    )
    parser.add_argument(
        "--paper", choices=("a4", "us-letter"), help="Paper format (default: a4)"
    )
    for name in ("cover", "toc"):
        parser.add_argument(
            f"--{name}", action=argparse.BooleanOptionalAction, default=None
        )
    parser.add_argument(
        "--toc-depth",
        type=int,
        choices=range(1, 7),
        help="Contents levels (default: 2)",
    )
    parser.add_argument(
        "--link-base", help="HTTP(S) folder URL publishing the current directory"
    )
    parser.add_argument(
        "--font-path",
        type=Path,
        action="append",
        help="Additional local font directory (repeatable)",
    )
    parser.add_argument(
        "--template-option",
        action="append",
        default=[],
        metavar="KEY=JSON",
        help="Namespaced template option (repeatable)",
    )
    return parser


def _settings(args: argparse.Namespace) -> Settings:
    path = args.config
    if path is None and not args.no_config and Path("typoprint.toml").is_file():
        path = Path("typoprint.toml")
    if args.preset is not None and (path is None or args.no_config):
        raise ConfigurationError("--preset requires a project configuration")
    base = load_settings(path, preset=args.preset) if path is not None else Settings()
    data = {
        key: value
        for key, value in vars(args).items()
        if key in Settings.model_fields and value is not None
    }
    for item in args.meta:
        key, separator, value = item.partition("=")
        if (
            not separator
            or key not in ("title", "subtitle", "author", "date", "version")
            or not value.strip()
        ):
            raise ConfigurationError("--meta expects a supported KEY=VALUE")
        if key in data:
            raise ConfigurationError(f"Metadata field supplied twice: {key}")
        data[key] = value
    if args.font_path is not None:
        data["font_paths"] = args.font_path
    if args.template_option:
        options = {}
        for item in args.template_option:
            key, separator, value = item.partition("=")
            if not separator or not key or key in options:
                raise ConfigurationError("--template-option expects a unique KEY=JSON")
            try:
                options[key] = json.loads(value)
            except ValueError as error:
                raise ConfigurationError(
                    f"Invalid JSON for template option {key}"
                ) from error
        data["template_options"] = options
    return base.with_overrides(Settings.model_validate(data))


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        settings = _settings(args)
        if "-" in args.paths:
            if (
                args.paths != ["-"]
                or args.order is not None
                or args.recursive
                or args.exclude
                or args.by_folder
                or args.strict
            ):
                raise ConfigurationError(
                    "stdin cannot be combined with file discovery options"
                )
            document = Document(
                chapters=(
                    Chapter(markdown=sys.stdin.buffer.read().decode("utf-8-sig")),
                )
            )
            plan = None
            default_name = "document"
        else:
            plan = plan_files(
                args.paths,
                order=args.order,
                recursive=args.recursive,
                exclude=args.exclude,
                by_folder=args.by_folder,
                strict=args.strict,
                lang=settings.lang,
            )
            document = document_from_plan(plan)
            first = Path(args.paths[0]) if args.paths else plan.root
            default_name = first.name if first.is_dir() else first.stem
        if args.dry_run:
            resolved = inspect_document(document, settings)
            resolved.pop("toc-depth", None)
            resolved.pop("chapter-level", None)
            print(
                json.dumps(
                    {
                        "files": [
                            {"name": chapter.name, "part": chapter.part}
                            for chapter in document.chapters
                        ],
                        "settings": resolved,
                        "warnings": list(plan.warnings) if plan is not None else [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        output = args.output or f"{default_name}.pdf"
        if output != "-" and plan is not None:
            destination = Path(output).resolve()
            if destination in {entry.path.resolve() for entry in plan.files}:
                raise ConfigurationError("PDF output would overwrite an input file")
        result = (
            render(document, settings=settings)
            if plan is None
            else render_files(plan, settings=settings)
        )
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        if output == "-":
            sys.stdout.buffer.write(result.content)
            sys.stdout.buffer.flush()
        else:
            destination = write_pdf(result, output)
            print(destination, file=sys.stderr)
        return 0
    except (TypoprintError, ValidationError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
