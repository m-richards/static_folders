from __future__ import annotations
import os
import typing
from collections.abc import Sequence
from pathlib import Path
from typing_extensions import Self, TypeVar, Generic, ClassVar, Type

from attrs import define, field

from static_folders import Folder
from static_folders.folder_interface import FolderLike

T = TypeVar("T", bound=Folder)
U = TypeVar("U", bound=Folder)

@define(slots=False)
class FolderPartition(FolderLike[U]): # TODO check double inherit works
    _raw_location: os.PathLike | str
    partition_class: Type[U] = field(kw_only=True)
    location: Path = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.location = Path(os.fspath(self._raw_location))

    @classmethod
    def from_string(cls, path: str) -> Self:
        """Alternate constructor from string (for discoverability"""
        return cls(path)

    def __fspath__(self) -> str:
        return str(self.location)

    @typing.overload
    def get_subfolder(self, name: str, subfolder_class: None = ...) -> U:
        ...

    @typing.overload
    def get_subfolder(self, name: str, subfolder_class: Type[T] = ...) -> T:
        ...

    # TODO maybe adhering to the common api here is confusing?
    def get_subfolder(self, name: str, subfolder_class: Type[T] | None = None) -> T | U:
        if subfolder_class is None:
            # Note, deliberately don't reference get_partition, don't want to play
            # subclass hierarchy jumping game
            return self.partition_class(self.location / name)
        else:
            return subfolder_class(self.location / name)

    def get_partition(self, name:str) ->U:
        """Extra Api to explicit reference a partition."""
        return self.partition_class(self.location / name)

    def create(self, *, mode: int = 0o777, parents: bool = True, exist_ok: bool = True) -> None:
        """Materialise folder representation to directories on disk.

        Variant on Pathlib.mkdir() with more sensible defaults for static folders context"""
        self.to_path().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)


@define(slots=False)
class EnumeratedFolderPartition(FolderPartition[U]):
    """Variant of FolderPartition, where conforming subfolders are known ahead of time.

    This behaves very much like a FolderPartition, but knowing subfolders means that `create`
    can materialise child dirs to avoid file/folder not found issues.
    """
    partition_names: ClassVar[Sequence[str]]
    # TODO partition prefix?


    def get_partition(self, name:str) ->U:
        """Extra Api to explicit reference a partition. Raises a NameError if partition isn't pre-defined.

        Note that if override access is required to append a partition, you can use
        folder.get_subfolder(name, subfolder_class=type(folder)). Omitting subfolder_class will trigger the same validation
        as in get_partition.
        """
        if name not in self.partition_names:
            # TODO should this warn instead?
            raise NameError(f"Received partition name {name!r} which is not defined in `partition_names`."
                            f"Use get_subfolder() to access a non conforming subfolder.")
        return self.partition_class(self.location / name)

    def create(self, *, mode: int = 0o777, parents: bool = True, exist_ok: bool = True) -> None:
        """Materialise folder representation to directories on disk. Recursively populates child folders to disk.

        Variant on Pathlib.mkdir() with more sensible defaults for static folders context"""
        self.to_path().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        for partition in self.partition_names:
            self.get_subfolder(partition).create(mode=mode, parents=False, exist_ok=exist_ok)

