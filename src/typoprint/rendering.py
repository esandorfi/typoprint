"""Per-call Typst compilation shared by every public surface."""

import json
import shutil
from collections.abc import Mapping, Sequence
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

import typst

from typoprint.models import (
    Chapter,
    ConfigurationError,
    Document,
    PrintPlan,
    RenderError,
    RenderResult,
    RuleError,
    Settings,
    Transform,
    Validator,
    relative_name,
)
from typoprint.planning import plan_files, read_markdown

MAIN = b"""#import "@local/typoprint:0.1.0": print-documents
#print-documents(path => read(path), (source, ..args) => image(source, ..args))
"""
INSPECT = b"""#import "@local/typoprint:0.1.0": inspect-inputs
#metadata(inspect-inputs()) <typoprint-settings>
"""
ASSETS = b"""#import "@local/typoprint:0.1.0": inspect-assets
#inspect-assets()
"""


def render(
    markdown_or_document: str | Document,
    *,
    settings: Settings | None = None,
    overrides: Settings | None = None,
    assets: Mapping[str, bytes] | None = None,
    transforms: Sequence[Transform] = (),
    validators: Sequence[Validator] = (),
) -> RenderResult:
    """Render Markdown to PDF bytes, reading only explicitly supplied assets.

    Asset keys are POSIX paths relative to the document root; image references
    are relative to each chapter's name. All extensions are trusted caller code.
    """
    document = (
        Document(chapters=(Chapter(markdown=markdown_or_document),))
        if isinstance(markdown_or_document, str)
        else markdown_or_document
    )
    options = _settings(settings, overrides)
    if options.link_base is not None:
        raise ConfigurationError("link_base requires filesystem inputs")
    document = _apply_rules(document, transforms, validators)
    with TemporaryDirectory(prefix="typoprint-") as temporary:
        root = Path(temporary)
        _stage_assets(assets or {}, root)
        return _compile(document, options, root)


def render_files(
    paths: Sequence[str | Path] | PrintPlan = (),
    *,
    settings: Settings | None = None,
    overrides: Settings | None = None,
    order: str | Path | None = None,
    recursive: bool = False,
    exclude: Sequence[str] = (),
    by_folder: bool = False,
    strict: bool = False,
    transforms: Sequence[Transform] = (),
    validators: Sequence[Validator] = (),
) -> RenderResult:
    """Render files or an inspected plan without modifying the source files."""
    options = _settings(settings, overrides)
    if isinstance(paths, PrintPlan):
        if order is not None or recursive or exclude or by_folder or strict:
            raise ConfigurationError("A PrintPlan replaces discovery options")
        plan = paths
    else:
        plan = plan_files(
            paths,
            order=order,
            recursive=recursive,
            exclude=exclude,
            by_folder=by_folder,
            strict=strict,
            lang=options.lang,
        )
    document = _apply_rules(document_from_plan(plan), transforms, validators)
    source_root = plan.root.resolve()
    with TemporaryDirectory(prefix="typoprint-files-") as temporary:
        root = Path(temporary)
        _snapshot_assets(document, source_root, root)
        result = _compile(document, options, root, link_root=source_root)
    return RenderResult(
        content=result.content, warnings=plan.warnings + result.warnings
    )


def document_from_plan(plan: PrintPlan) -> Document:
    root = plan.root.resolve()
    chapters: list[Chapter] = []
    for entry in plan.files:
        path = entry.path.resolve()
        if not path.is_relative_to(root):
            raise RenderError(f"{path}: input escapes the render root {root}")
        chapters.append(
            Chapter(
                name=path.relative_to(root).as_posix(),
                markdown=read_markdown(path),
                part=entry.part,
            )
        )
    return Document(chapters=tuple(chapters))


def inspect_document(document: Document, settings: Settings) -> dict[str, object]:
    """Resolve front matter and automatic choices without rendering document bodies."""
    with TemporaryDirectory(prefix="typoprint-inspect-") as temporary:
        with as_file(files("typoprint") / "resources") as resources:
            compiler = _compiler(
                INSPECT,
                Path(temporary),
                resources,
                _payload(document, settings, None),
                resources / "packages",
                settings,
            )
            try:
                result = json.loads(
                    compiler.query(
                        "<typoprint-settings>",
                        field="value",
                        one=True,
                    )
                )
            except typst.TypstError as error:
                raise RenderError(_diagnostic(error)) from error
    if not isinstance(result, dict):
        raise RenderError("Could not inspect document metadata")
    return result


def _settings(settings: Settings | None, overrides: Settings | None) -> Settings:
    base = settings or Settings()
    return base.with_overrides(overrides) if overrides is not None else base


def _apply_rules(
    document: Document,
    transforms: Sequence[Transform],
    validators: Sequence[Validator],
) -> Document:
    chapters: list[Chapter] = []
    for chapter in document.chapters:
        markdown = chapter.markdown
        try:
            for transform in transforms:
                markdown = transform(markdown)
                if not isinstance(markdown, str):
                    raise RuleError("Transformations must return Markdown text")
            for validator in validators:
                validator(markdown)
        except RuleError:
            raise
        except Exception as error:
            # Callback code is outside the library. Do not include its message,
            # which may contain confidential Markdown, in automatic diagnostics.
            raise RuleError(f"Rule failed for chapter {chapter.name}") from error
        chapters.append(
            Chapter(name=chapter.name, markdown=markdown, part=chapter.part)
        )
    return Document(chapters=tuple(chapters))


def _stage_assets(assets: Mapping[str, bytes], root: Path) -> None:
    for name, content in assets.items():
        try:
            safe_name = relative_name(name)
        except ValueError as error:
            raise RenderError(f"Invalid asset name: {name!r}") from error
        if not isinstance(content, bytes):
            raise RenderError("Asset values must be bytes")
        target = root / safe_name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as error:
            raise RenderError(f"Cannot stage asset {name}") from error


def _snapshot_assets(document: Document, source_root: Path, destination: Path) -> None:
    """Resolve actual image files before copying them into a private render root.

    Typst's lexical project root follows filesystem symlinks. Canonicalize each
    referenced resource here, then compile only the isolated snapshot. cmarker
    discovers image references so HTML images and Markdown share one parser.
    """
    with as_file(files("typoprint") / "resources") as resources:
        compiler = _compiler(
            ASSETS,
            destination,
            resources,
            _payload(document, Settings(), None),
            resources / "packages",
            Settings(),
        )
        try:
            references = json.loads(compiler.query("<typoprint-asset>", field="value"))
        except typst.TypstError as error:
            raise RenderError(_diagnostic(error)) from error
    staged: set[Path] = set()
    for reference in references:
        source = reference["source"]
        if not isinstance(source, str) or ":" in source or "\\" in source:
            raise RenderError("Images must reference local POSIX paths")
        relative = (
            source.lstrip("/")
            if source.startswith("/")
            else reference["dir"] + "/" + source
        )
        relative = relative.lstrip("/")
        original = (source_root / relative).resolve()
        target = (destination / relative).resolve()
        if not original.is_relative_to(source_root) or not target.is_relative_to(
            destination
        ):
            raise RenderError(f"Image escapes the render root: {source}")
        if target in staged:
            continue
        try:
            content = original.read_bytes()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as error:
            raise RenderError(f"Cannot read image {source}: {error}") from error
        staged.add(target)


def _payload(document: Document, settings: Settings, base_dir: str | None) -> str:
    entries = []
    for chapter in document.chapters:
        path = PurePosixPath(chapter.name)
        entries.append(
            {
                "path": "/" + chapter.name,
                "dir": ""
                if path.parent == PurePosixPath(".")
                else path.parent.as_posix(),
                "stem": path.stem,
                "source": chapter.name,
                "part": chapter.part,
                "text": chapter.markdown,
            }
        )
    return json.dumps(
        {
            "settings": settings.model_dump(mode="json"),
            "files": entries,
            "base-dir": base_dir,
        },
        ensure_ascii=False,
    )


def _compile(
    document: Document,
    settings: Settings,
    root: Path,
    *,
    link_root: Path | None = None,
) -> RenderResult:
    base_dir = None
    if settings.link_base is not None:
        try:
            base_dir = (link_root or root).relative_to(Path.cwd().resolve()).as_posix()
            base_dir = "" if base_dir == "." else base_dir
        except ValueError as error:
            raise ConfigurationError(
                "link_base requires inputs under the working directory"
            ) from error
    with as_file(files("typoprint") / "resources") as resources:
        with TemporaryDirectory(prefix="typoprint-packages-") as temporary:
            packages = resources / "packages"
            if settings.template not in ("editorial", "report"):
                bundle = Path(settings.template).resolve()
                if not (bundle / "template.typ").is_file():
                    raise ConfigurationError(
                        f"Template bundle requires {bundle / 'template.typ'}"
                    )
                # A package import keeps bundle-local assets out of the source root.
                packages = Path(temporary) / "packages"
                shutil.copytree(resources / "packages", packages)
                custom = packages / "local/typoprint-custom/0.1.0"
                shutil.copytree(bundle, custom)
                (custom / "typst.toml").write_text(
                    '[package]\nname = "typoprint-custom"\nversion = "0.1.0"\n'
                    'entrypoint = "template.typ"\n',
                    encoding="utf-8",
                )
            compiler = _compiler(
                MAIN,
                root,
                resources,
                _payload(document, settings, base_dir),
                packages,
                settings,
            )
            try:
                content, warnings = compiler.compile_with_warnings(timestamp=0)
            except typst.TypstError as error:
                raise RenderError(
                    f"{_diagnostic(error)} (render root: {root})"
                ) from error
    if not isinstance(content, bytes):
        raise RenderError("Typst did not produce PDF bytes")
    return RenderResult(
        content=content, warnings=tuple(_diagnostic(w) for w in warnings)
    )


def _compiler(
    entrypoint: bytes,
    root: Path,
    resources: Path,
    payload: str,
    packages: Path,
    settings: Settings,
) -> typst.Compiler:
    for path in settings.font_paths:
        if not path.is_dir():
            raise ConfigurationError(f"Font directory not found: {path}")
    return typst.Compiler(
        input=entrypoint,
        root=root,
        sys_inputs={"options": payload},
        package_path=packages,
        package_cache_path=packages,
        font_paths=typst.Fonts(
            include_system_fonts=False,
            font_paths=[resources / "fonts", *settings.font_paths],
        ),
        ignore_system_fonts=True,
    )


def _diagnostic(error: typst.TypstError | typst.TypstWarning) -> str:
    return "; ".join(
        [error.message, *(hint for hint in error.hints if "--root" not in hint)]
    )
