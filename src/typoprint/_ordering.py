"""Tables of contents: one Markdown file fixing the order and parts of printed Markdown.

The order is a pure function of the file's text and the files found under its folder:
the file comes first, each `##` heading opens a part whose links place pages in reading
order, a folder link adds the rest of that folder in natural order, and files placed
nowhere come last.
"""

from __future__ import annotations

import posixpath
import re
import unicodedata
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple
from urllib.parse import unquote

from typoprint.models import Language as Language
from typoprint.models import RenderError as RenderError

UNPLACED_TITLE: dict[Language, str] = {"fr": "Autres pages", "en": "Other pages"}
_DIGITS = re.compile(r"([0-9]+)")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_PART = re.compile(r"^ {0,3}##[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_CODE_SPAN = re.compile(r"(`+).+?\1")
# Inline links and images: `[text](target "title")`; the leading `!` marks an image.
_LINK = re.compile(r"(!?)\[[^\]]*\]\(\s*<?([^\s)>]*)>?[^)]*\)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

NaturalKey = tuple[tuple[tuple[int, int, str], ...], str]
ReadingKey = tuple[tuple[int, int, NaturalKey], ...]


class TocPart(NamedTuple):
    title: str
    # Link targets in reading order, as written.
    targets: tuple[str, ...]


class PlannedGroup(NamedTuple):
    title: str
    pages: tuple[PurePosixPath, ...]


class OrderedMap(NamedTuple):
    root: Path
    # The table of contents itself, unless excluded.
    intro: PurePosixPath | None
    groups: tuple[PlannedGroup, ...]
    # Found under the root but placed nowhere: printed last, in natural order.
    unplaced: tuple[PurePosixPath, ...]

    def chapters(self, lang: Language) -> list[tuple[Path, str | None]]:
        """Files to print with the part each one opens."""
        chapters: list[tuple[Path, str | None]] = []
        if self.intro is not None:
            chapters.append((self.root / self.intro, None))
        for title, pages in (*self.groups, (UNPLACED_TITLE[lang], self.unplaced)):
            chapters.extend(
                (self.root / path, title if index == 0 else None)
                for index, path in enumerate(pages)
            )
        return chapters


def natural_key(name: str) -> NaturalKey:
    """Numbers by value, text without case, after NFC; the exact name breaks ties."""
    text = unicodedata.normalize("NFC", name)
    chunks = tuple(
        (0, int(chunk), "") if index % 2 else (1, 0, chunk.casefold())
        for index, chunk in enumerate(_DIGITS.split(text))
        if chunk
    )
    return chunks, text


def reading_order(relative: PurePosixPath) -> ReadingKey:
    # In each folder: README.md, the other files, then the subfolders.
    *folders, name = relative.parts
    return tuple((1, 0, natural_key(folder)) for folder in folders) + (
        (0, 0 if name.casefold() == "readme.md" else 1, natural_key(name)),
    )


def exclusion_patterns(patterns: Iterable[str]) -> list[str]:
    return [pattern.replace("\\", "/").strip("/") for pattern in patterns]


def excluded(relative: PurePosixPath, patterns: Sequence[str]) -> bool:
    # A pattern names a file or one of its folders, relative to the given directory.
    candidates = [relative, *relative.parents[:-1]]
    return any(
        candidate.full_match(pattern)
        for pattern in patterns
        for candidate in candidates
    )


def read_toc(text: str) -> tuple[TocPart, ...]:
    """`##` headings and the link targets under them, outside code, in reading order."""
    parts: list[TocPart] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = _FENCE.match(line)
        if fence is not None:
            # A fence closes on the same character, at least as long, alone on its line.
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = None
            continue
        if marker:
            fence = marker[1]
        elif heading := _PART.match(line):
            parts.append(TocPart(heading[1], ()))
        elif parts:
            targets = tuple(
                target
                for image, target in _LINK.findall(_CODE_SPAN.sub("", line))
                if not image
            )
            parts[-1] = parts[-1]._replace(targets=parts[-1].targets + targets)
    return tuple(parts)


def _key(text: str) -> PurePosixPath:
    # Paths compare in NFC with `/`; files keep their on-disk spelling for reading.
    return PurePosixPath(unicodedata.normalize("NFC", text.replace("\\", "/")))


def _local_target(target: str) -> PurePosixPath | None:
    """The path a link names under the table's folder, else None: web, anchor, outside."""
    if _SCHEME.match(target) or target.startswith(("#", "/")):
        return None
    path = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not path:
        return None
    normalized = posixpath.normpath(path.replace("\\", "/"))
    if normalized == ".." or normalized.startswith("../"):
        return None
    return _key(normalized)


def plan_order(path: Path, exclude: Sequence[str] = ()) -> OrderedMap:
    """Resolve a Markdown table of contents against the files found under its folder."""
    try:
        text = path.read_text(encoding="utf-8").removeprefix("﻿")
    except (OSError, UnicodeDecodeError) as error:
        raise RenderError(f"{path} : cannot read contents map ({error})") from error
    toc = read_toc(text)
    root = path.resolve().parent
    patterns = exclusion_patterns(exclude)
    found = {
        _key(relative.as_posix()): PurePosixPath(relative.as_posix())
        for relative in (
            child.relative_to(root)
            for child in root.rglob("*.md")
            if child.is_file() and child.suffix == ".md"
        )
    }
    printable = sorted(
        (actual for key, actual in found.items() if not excluded(key, patterns)),
        key=reading_order,
    )
    available = {_key(actual.as_posix()) for actual in printable}
    intro_key = _key(path.resolve().name)
    intro = found[intro_key] if intro_key in available else None
    placed: set[PurePosixPath] = {intro_key}

    def missing(target: str, what: str) -> RenderError:
        return RenderError(
            f"{path} : {target} ne désigne aucun {what} under {root} "
            "(exact spelling and case required)"
        )

    groups: list[PlannedGroup] = []
    for part in toc:
        pages: list[PurePosixPath] = []
        for target in part.targets:
            key = _local_target(target)
            if key is None:
                continue
            if key.suffix == ".md":
                if key in available:
                    matches = [found[key]]
                elif excluded(key, patterns):
                    # Listed for the map only: the exclusions keep it out of the PDF.
                    continue
                else:
                    raise missing(target, "printable Markdown file")
            elif (root / key).is_dir() or target.split("#", 1)[0].endswith("/"):
                # A folder brings its pages not yet placed, in reading order.
                inside = key == PurePosixPath(".")
                if not inside and not any(key in other.parents for other in found):
                    raise missing(target, "Markdown folder")
                matches = [
                    actual
                    for actual in printable
                    if inside or key in _key(actual.as_posix()).parents
                ]
            else:
                continue
            for actual in matches:
                if _key(actual.as_posix()) not in placed:
                    placed.add(_key(actual.as_posix()))
                    pages.append(actual)
        groups.append(PlannedGroup(part.title, tuple(pages)))
    unplaced = tuple(
        actual for actual in printable if _key(actual.as_posix()) not in placed
    )
    return OrderedMap(root, intro, tuple(groups), unplaced)
