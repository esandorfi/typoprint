"""Plan filesystem inputs before rendering or writing any output."""

import os
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from typoprint._ordering import excluded, exclusion_patterns, plan_order, reading_order
from typoprint.models import Language, PlannedFile, PrintPlan, RenderError


def plan_files(
    paths: Sequence[str | Path] = (),
    *,
    order: str | Path | None = None,
    recursive: bool = False,
    exclude: Sequence[str] = (),
    by_folder: bool = False,
    strict: bool = False,
    lang: Language = "fr",
) -> PrintPlan:
    """Inspect the exact file order, part openings, and unplaced-page warnings."""
    if order is not None and (paths or recursive or by_folder):
        raise RenderError("order replaces paths, recursive, and by_folder")
    if strict and order is None:
        raise RenderError("strict requires order")
    if order is not None:
        toc = plan_order(Path(order), exclude)
        if toc.unplaced and strict:
            raise RenderError("Pages outside the contents map: " + _names(toc.unplaced))
        files = tuple(
            PlannedFile(path=path.resolve(), part=part)
            for path, part in toc.chapters(lang)
        )
        warnings = (
            ("Pages outside the contents map, appended: " + _names(toc.unplaced),)
            if toc.unplaced
            else ()
        )
        root = toc.root
    else:
        sources: list[Path] = []
        patterns = exclusion_patterns(exclude)
        for value in paths:
            path = Path(value).resolve()
            if not path.is_dir():
                sources.append(path)
                continue
            candidates = path.rglob("*.md") if recursive else path.glob("*.md")
            found = {
                PurePosixPath(child.relative_to(path).as_posix()): child
                for child in candidates
                if child.is_file() and child.suffix == ".md"
            }
            kept = sorted(
                (key for key in found if not excluded(key, patterns)), key=reading_order
            )
            if not kept:
                raise RenderError(f"{path}: no Markdown files to print")
            sources.extend(found[key] for key in kept)
        if not sources:
            raise RenderError("No Markdown inputs")
        if len(set(sources)) != len(sources):
            raise RenderError("A Markdown file was selected more than once")
        try:
            root = Path(os.path.commonpath([path.parent for path in sources]))
        except ValueError as error:
            raise RenderError("Inputs must be on the same drive") from error
        entries: list[PlannedFile] = []
        previous: str | None = None
        for path in sources:
            directory = path.parent.relative_to(root).as_posix()
            folder = root.name if directory == "." else directory
            part = folder if by_folder and folder != previous else None
            entries.append(PlannedFile(path=path, part=part))
            previous = folder
        files, warnings = tuple(entries), ()
    if not files:
        raise RenderError("No Markdown inputs")
    for entry in files:
        if not entry.path.is_relative_to(root):
            raise RenderError(f"{entry.path}: input escapes the render root {root}")
        read_markdown(entry.path)
    return PrintPlan(root=root, files=files, warnings=warnings)


def read_markdown(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise RenderError(f"{path}: cannot read Markdown ({error})") from error
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        line = content.count(b"\n", 0, error.start) + 1
        raise RenderError(f"{path}:{line}: invalid UTF-8") from error


def _names(paths: Sequence[PurePosixPath]) -> str:
    return ", ".join(path.as_posix() for path in paths)
