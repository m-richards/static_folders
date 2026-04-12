from __future__ import annotations

import inspect
import os
import sys
import typing
from pathlib import Path
from typing import Sequence, Any, Callable, TypeVar, ClassVar, Type

from attrs import define, field, Factory
from typing_extensions import Self

from static_folders.folder_interface import FolderLike

if typing.TYPE_CHECKING:
    from types import ModuleType
else:
    ModuleType = Type[Any]

U = TypeVar("U", bound="Folder")

PathLike = typing.Union[str, Path]
T = TypeVar("T", bound="Folder")

V = TypeVar("V")


def _get_annotations(obj: Callable[..., object] | type[Any] | ModuleType) -> dict[str, object]:
    if sys.version_info >= (3, 10):
        return inspect.get_annotations(obj)
    # https://docs.python.org/3/howto/annotations.html#accessing-the-annotations-dict-of-an-object-in-python-3-9-and-older
    else:
        if isinstance(obj, type):
            ann = obj.__dict__.get("__annotations__", {})
        else:
            ann = getattr(obj, "__annotations__", {})
        return ann


@define(slots=True)  # messes type annotation detection for nested classes up
class Folder(FolderLike):
    """Representation of a Folder on disk, containing standard files or subfolders.

    ```
    class Photos(Folder):
        temp: Folder
        y2024: PhotoYearFolder
        y2025: PhotoYearFolder = PhotoYearFolder(Path("2025"))  # provide concrete which doesn't have y prefix
        y2026: PhotoYearFolder = PhotoYearFolder("2026")  # string arg is fine too
        readme: Path = Path("readme.md")
    ```
    """

    _raw_location: os.PathLike | str
    location: Path = field(init=False)

    _reserved_attributes: ClassVar[Sequence[str]] = [
        "location",
        "_reserved_attributes",
        "_raw_location",
        "_child_folders",
    ]
    _child_folders: list[FolderLike] = field(init=False, default=Factory(list))

    @classmethod
    def from_path(cls, path: Path) -> Folder:
        return cls(path)

    @classmethod
    def from_string(cls, path: str) -> Self:
        """Alternate constructor from string (for discoverability"""
        return cls(path)

    def __fspath__(self) -> str:
        return str(self.location)

    def __attrs_post_init__(self) -> None:  # noqa: PLR0912
        self.location = Path(os.fspath(self._raw_location))
        cls = type(self)
        # custom support for annotations which are sub-types of Folder, or Path
        # these are bound as "child-dir" objects
        annotations = _get_annotations(cls)

        folder_type_fields = [
            k
            for k, v in cls.__dict__.items()
            if isinstance(v, (FolderLike, Path))
            # __qualname__ is used to detect if something is a nested FolderLike class (it will have __qualname__
            # defined to show nest hierarchy, but an instance won't)
            and not hasattr(v, "__qualname__")
        ]

        covered_keys = set(annotations.keys()).union(self._reserved_attributes)
        fields_wo_annotations = [i for i in folder_type_fields if i not in covered_keys]
        if len(fields_wo_annotations) > 0:
            # TODO ideally would do this at "compile time" but I probably don't want a metaclass just for that
            # (but could I do it with a decorator, like attrs?)
            msg = (
                "Folder subclasses do not support FolderLike or Path type fields without type annotations, "
                f"to avoid confusing error cases. Fields {fields_wo_annotations} are missing annotations."
            )
            raise TypeError(msg)

        # resolve all the child attributes from annotations into instance objects
        for attrib_name, annotation in annotations.items():
            if attrib_name in self._reserved_attributes:
                continue
            if isinstance(annotation, type):
                if issubclass(annotation, FolderLike):  # e.g. `foo: Folder`
                    value = getattr(self, attrib_name, None)
                    folder_name = None
                    if value is None:  # check default wasn't given
                        folder_name = attrib_name
                    elif isinstance(value, FolderLike):  # `foo: Folder = Folder("bar")` -> foo / "bar"
                        folder_name = value.location.name
                    elif isinstance(value, Path):  # `foo: Folder = Path("bar")`
                        # This is not permitted by the type system, but is an easy typo someone could make
                        # which would lead to confusing behaviour - the path wouldn't be "seen" at all.
                        msg = (
                            f"Annotating an attribute with a FolderLike type and a Path value is incorrect "
                            f"and not supported. For class `{type(self).__name__}` got:\n"
                            f"'{attrib_name}: {annotation} = {value!r}'\n"
                            f"If you intended to declare a subfolder with a custom folder name, "
                            f"you should use `{attrib_name}: FolderLike: FolderLike(name)` instead.\n"
                            f"If you intended to declare a file within the folder, you should use"
                            f" `{attrib_name}: Path: Path(name)` "
                            f"instead."
                        )
                        raise TypeError(msg)
                    else:
                        pass  # subclasses or lambda come through this passage
                        # print("pre-existing thing", value)
                    if folder_name is not None:
                        try:
                            value = annotation.from_path(self.location / folder_name)
                        except TypeError as e:
                            msg = (
                                f"Building Class {type(self).__name__} failed on constructing attribute:\n"
                                f"'{attrib_name}: {annotation} = {value!r}' with attached error"
                            )
                            raise TypeError(msg) from e
                        setattr(self, attrib_name, value)

                        self._child_folders.append(value)
                    # else: # extract path from given default
                    #     setattr(self, attrib_name, annotation(self.location / os.fspath(value)))

                elif issubclass(annotation, Path):
                    provided_path: Path = getattr(self, attrib_name)
                    if not isinstance(provided_path, Path):
                        msg = (
                            f"Annotation for attribute {attrib_name!r} was Path, "
                            f"but provided attribute was {provided_path!r}"
                        )
                        raise TypeError(msg)
                    if provided_path.is_absolute():
                        msg = (
                            "Provided path instances must be relative paths, these are treated as "
                            "paths relative to the location of the Folder stance. This was not true "
                            f"for {attrib_name!r}"
                        )
                        raise TypeError(msg)
                    setattr(self, attrib_name, self.location / provided_path)
                elif issubclass(annotation, str):
                    msg = (
                        "Folder subclasses do not support raw str annotated fields, "
                        f"to avoid confusion between whether the str represents a Path or not. Got {attrib_name!r} "
                        f"which is annotated as a string. If your intention is to provide a relative filepath, "
                        f"provide a Path instead. If your intention is to declare a class variable string, "
                        f"use the full ClassVar[str] annotation to convey this."
                    )
                    raise TypeError(msg)

    def to_path(self) -> Path:
        return self.location

    def get_file(self, name: str) -> Path:
        return self.location / name

    @typing.overload
    def get_subfolder(self, name: str, subfolder_class: None = ...) -> Folder: ...

    @typing.overload
    def get_subfolder(self, name: str, subfolder_class: Type[T] = ...) -> T: ...

    def get_subfolder(self, name: str, subfolder_class: Type[T] | None = None) -> T | Folder:
        if subfolder_class is None:
            return Folder(self.location / name)
        else:
            return subfolder_class(self.location / name)

    def create(self, *, mode: int = 0o777, parents: bool = True, exist_ok: bool = True) -> None:
        """Materialise folder representation to directories on disk. Recursively populates child folders to disk.

        Variant on Pathlib.mkdir() with more sensible defaults for static folders context"""
        self.to_path().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        for child in self._child_folders:
            # children won't need to create parents because that's ensured above
            child.create(mode=mode, parents=False, exist_ok=exist_ok)
