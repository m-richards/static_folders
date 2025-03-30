from __future__ import annotations

import inspect
import os
import typing
from pathlib import Path

from attrs import define, field, Factory
from typing_extensions import Type, TypeVar, Self, ClassVar
from typing import Sequence

U = TypeVar("U", bound="Folder")


@define(slots=False)
class Folder:
    _raw_location: os.PathLike| str
    location: Path = field(init=False)

    _reserved_attributes: ClassVar[Sequence[str]] = [
        "location",
        "_reserved_attributes",
        "_raw_location",
        "_child_folders",
    ]
    _child_folders: list["Folder"] = field(init=False, default=Factory(list))

    @classmethod
    def from_string(cls, path: str) -> Self:
        """Alternate constructor from string (for discoverability"""
        return cls(path)

    def __fspath__(self) -> str:
        return str(self.location)

    def __attrs_post_init__(self) -> None:
        self.location = Path(os.fspath(self._raw_location))
        cls = type(self)
        # custom support for annotations which are sub-types of Folder, or Path
        # these are bound as "child-dir" objects
        annotations = inspect.get_annotations(cls)

        for attrib_name, annotation in annotations.items():
            if attrib_name in self._reserved_attributes:
                continue
            if isinstance(annotation, type):
                if issubclass(annotation, Folder):  # i.e. attribute foo: Folder - a class constructor
                    value = getattr(self, attrib_name, None)
                    if value is None:  # check default wasn't given
                        value = annotation(self.location / attrib_name)
                        setattr(self, attrib_name, value)
                    self._child_folders.append(value)
                    # else: # extract path from given default
                    #     setattr(self, attrib_name, annotation(self.location / os.fspath(value)))

                elif issubclass(annotation, Path):
                    provided_path: Path = getattr(self, attrib_name)
                    if not isinstance(provided_path, Path):
                        msg = (f"Annotation for attribute {attrib_name} was Path, "
                               f"but provided attribute was {provided_path!r}")
                        raise TypeError(msg)
                    if provided_path.is_absolute():
                        msg = (
                            "Provided path instances must be relative paths, these are treated as "
                            "paths relative to the location of the Folder stance."
                        )
                        raise TypeError(msg)
                    setattr(self, attrib_name, self.location / provided_path)

    def to_path(self) -> Path:
        return self.location

    def get_file(self, name: str) -> Path:
        return self.location / name

    @typing.overload
    def get_subfolder(self, name: str, subclass_class: None = ...) -> "Folder": ...

    @typing.overload
    def get_subfolder(self, name: str, subclass_class: Type[U] = ...) -> U: ...

    def get_subfolder(self, name: str, *, subfolder_class: Type[U]| None = None) -> U| "Folder":
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
