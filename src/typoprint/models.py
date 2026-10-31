"""Public values for planning, configuration, and rendering."""

from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

Language = Literal["fr", "en"]
Paper = Literal["a4", "us-letter"]
METADATA_FIELDS = ("title", "subtitle", "author", "date", "version")


class TypoprintError(ValueError):
    """Base error safe to catch at a transport boundary."""


class ConfigurationError(TypoprintError):
    """Invalid settings, template bundle, or configuration file."""


class RenderError(TypoprintError):
    """Invalid inputs or a failed PDF compilation.

    Compiler diagnostics may quote source text. Applications decide whether
    to expose these details; the library never logs document contents.
    """


class RuleError(TypoprintError):
    """A developer-supplied transformation or validation rule refused input."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def relative_name(value: str) -> str:
    """A portable, non-traversing resource path, never a host filesystem path."""
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or "\x00" in value
        or value.startswith("/")
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise ValueError("Expected a relative POSIX path without '.', '..', or a drive")
    return PurePosixPath(value).as_posix()


class Chapter(FrozenModel):
    name: str = "document.md"
    markdown: str
    part: str | None = None

    _name = field_validator("name")(relative_name)


class Document(FrozenModel):
    chapters: tuple[Chapter, ...] = Field(min_length=1)

    @field_validator("chapters")
    @classmethod
    def unique_names(cls, chapters: tuple[Chapter, ...]) -> tuple[Chapter, ...]:
        if len({chapter.name for chapter in chapters}) != len(chapters):
            raise ValueError("Chapter names must be unique")
        return chapters


class Settings(FrozenModel):
    """Rendering settings. Fields explicitly set survive layered merging.

    None for an optional metadata field means inherit front matter. False
    disables automatic cover/contents choices explicitly.
    """

    template: str = "editorial"
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None
    version: str | None = None
    lang: Language = "fr"
    paper: Paper = "a4"
    toc: bool | None = None
    toc_depth: int = Field(default=2, ge=1, le=6)
    cover: bool = False
    link_base: str | None = None
    font_paths: tuple[Path, ...] = ()
    template_options: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("template")
    @classmethod
    def nonempty_template(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "Template must name a built-in layout or a bundle directory"
            )
        return value

    @field_validator("link_base")
    @classmethod
    def web_folder(cls, value: str | None) -> str | None:
        if value is not None:
            if not value.startswith(("https://", "http://")) or any(
                char.isspace() for char in value
            ):
                raise ValueError("link_base must be an HTTP(S) folder URL")
            return value.rstrip("/") + "/"
        return None

    def with_overrides(self, overrides: "Settings") -> "Settings":
        """Merge only explicitly supplied fields; nested options replace as a unit."""
        return Settings.model_validate(
            self.model_dump(exclude_unset=True)
            | overrides.model_dump(exclude_unset=True)
        )


class RenderResult(FrozenModel):
    content: bytes
    warnings: tuple[str, ...] = ()


class PlannedFile(FrozenModel):
    path: Path
    part: str | None = None


class PrintPlan(FrozenModel):
    root: Path
    files: tuple[PlannedFile, ...] = Field(min_length=1)
    warnings: tuple[str, ...] = ()


Transform = Callable[[str], str]
Validator = Callable[[str], None]
