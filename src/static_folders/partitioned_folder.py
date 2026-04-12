from __future__ import annotations

import os
import typing
from pathlib import Path

from attrs import define, field
from typing_extensions import TypeVar, ClassVar, Type, Self

from static_folders import Folder
from static_folders.folder_interface import FolderLike

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

T = TypeVar("T", bound=Folder)
U = TypeVar("U", bound=Folder)


@define(slots=False)
class FolderPartition(FolderLike[U]):
    _raw_location: os.PathLike | str
    partition_class: type[U] = field(init=False, repr=False)
    location: Path = field(init=False)

    partition_prefix: ClassVar[str] = ""

    @classmethod
    def from_path(cls, path: Path) -> FolderPartition:
        return cls(path)

    def __attrs_post_init__(self) -> None:
        self.location = Path(os.fspath(self._raw_location))
        # runtime safety check
        if getattr(type(self), "_type_param", None) is None:
            # TODO should this be a warning instead? we're crashing on what's usually valid python
            # TODO wish we could do this in a static analysis safe way. But the crash happens at
            #  class definition time (unless you're using a FolderPartition as solely a toplevel thing),
            #  not instantiation time which for now seems safe enough
            msg = (
                "FolderPartition instance constructed without providing explicit generics. "
                "We can't construct partition folder types properly without this. "
                "You should write e.g. "
                "attr: FolderPartition[SomeClass] = FolderPartition[SomeClass](...) not bare FolderPartition(...)"
            )
            raise TypeError(msg)
        else:
            # bind the captured type parameter to the instance
            self.partition_class = type(self)._type_param  # type:ignore[attr-defined]

    @classmethod
    def __class_getitem__(cls, item: Type[U]) -> Self:
        """Class Getitem is called when you call square brackets (getitem) on a class.
        i.e. when you call the constructor of a generic class with explicit type annotations
        f= FolderPartition[SomeClass](path)

        We override __class_getitem__ to create a subclass of FolderPartition on which we store
        the class provided in square brackets so our instance f has access to it. We do this at
        runtime using the 3-argument call to type() which creates new types.

        in spirit, we're doing:
        ```
        class FolderParitionSomeClass(FolderPartition[SomeClass]):
            _type_param = SomeClass


        f = FolderParitionSomeClass(path)
        # or more directly
        ```
        inline dynamically. Note right now there's no cache, so each FolderParitionSomeClass instance
        is unrelated.
        """
        if isinstance(item, TypeVar):
            # This is called at class definition time where item is a Generic, don't do anything crazy
            # (this is equivalent to super().__class_getitem__(item))
            return cls
        # Otherwise we specialise PartitionedFolder[Kind]
        # and make a new subclass of PartitionedFolder, which we call PartitionedFolder[Kind_static_folders_dynamic]
        # with the suffix embedded so that a user can see there's some spooky magic going on if
        # they ever assign x = FolderPartition[SomeClass] and look at x
        subclass = type(f"{cls.__name__}[{item.__name__}_static_folders_dynamic]", (cls,), {})
        subclass._type_param = item  # type:ignore[attr-defined]
        return subclass  # type:ignore[return-value]

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
