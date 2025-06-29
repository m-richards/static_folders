from __future__ import annotations

import os
import typing
from pathlib import Path

from attrs import define, field
from typing_extensions import TypeVar, ClassVar, Type

from static_folders import Folder
from static_folders.folder_interface import FolderLike

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

T = TypeVar("T", bound=Folder)
U = TypeVar("U", bound=Folder)


@define(slots=False)
class FolderPartition(FolderLike[U]):
    _raw_location: os.PathLike | str
    partition_class: Type[U] = field(kw_only=True)
    location: Path = field(init=False)

    partition_prefix: ClassVar[str] = ""

    def __attrs_post_init__(self) -> None:
        self.location = Path(os.fspath(self._raw_location))

    def __fspath__(self) -> str:
        return str(self.location)

    @typing.overload
    def get_subfolder(self, name: str, subfolder_class: None = ...) -> Folder: ...

    @typing.overload
    def get_subfolder(self, name: str, subfolder_class: Type[T] = ...) -> T: ...

    def get_subfolder(self, name: str, subfolder_class: Type[T] | None = None) -> T | Folder:
        """Retrieve a subfolder.

        Note that this is convenience similar to a regular folder. To get a partition entry, use get_partition.
        """
        if subfolder_class is None:
            return Folder(self.location / name)
        else:
            return subfolder_class(self.location / name)

    def get_partition(self, name: str) -> U:
        """Extra Api to explicit reference a partition."""
        if name.startswith(self.partition_prefix) is False:
            name = f"{self.partition_prefix}{name}"
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
    partition_names_expanded: Sequence[str] = field(init=False)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        self.partition_names_expanded = [f"{self.partition_prefix}{n}" for n in self.partition_names]

    def get_partition(self, name: str) -> U:
        """Extra Api to explicit reference a partition. Raises a NameError if partition isn't pre-defined.

        Note that if override access is required to append a partition, you can use
        folder.get_subfolder(name, subfolder_class=type(folder)),
        but omitting subfolder_class will trigger the same validation as in get_partition.
        """
        if name in self.partition_names:
            name = f"{self.partition_prefix}{name}"

        if name not in self.partition_names_expanded:
            # TODO should this warn instead?
            msg = (
                f"Received partition name {name!r} which is not defined in `partition_names`."
                f"Use get_subfolder() to access a non conforming subfolder."
            )
            raise NameError(msg)
        return self.partition_class(self.location / name)

    def create(self, *, mode: int = 0o777, parents: bool = True, exist_ok: bool = True) -> None:
        """Materialise folder representation to directories on disk. Recursively populates child folders to disk.

        Variant on Pathlib.mkdir() with more sensible defaults for static folders context"""
        self.to_path().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        for partition in self.partition_names_expanded:
            self.get_subfolder(partition).create(mode=mode, parents=False, exist_ok=exist_ok)
