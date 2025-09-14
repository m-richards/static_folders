from __future__ import annotations
from abc import ABC, abstractmethod

import typing

from typing_extensions import Type, TypeVar, Generic

if typing.TYPE_CHECKING:
    from pathlib import Path

T = TypeVar("T")


class FolderLike(ABC, Generic[T]):
    location: Path

    # LSP doesn't realist that attrs implements this
    # @abstractmethod
    # def __init__(self, location: Path) -> None: ...
    @classmethod
    @abstractmethod
    def from_path(cls, path: Path) -> FolderLike[T]:
        pass

    @abstractmethod
    def __fspath__(self) -> str: ...

    def to_path(self) -> Path:
        # going to not follow the advice of https://hynek.me/articles/python-subclassing-redux/
        # since this should be the behaviour in all sane cases
        return self.location

    def get_file(self, name: str) -> Path:
        # going to not follow the advice of https://hynek.me/articles/python-subclassing-redux/
        # since this should be the behaviour in all sane cases
        return self.location / name

    @abstractmethod
    def get_subfolder(self, name: str, subfolder_class: Type[T] = ...) -> T:
        # TODO is this a bad idea? we will have other @overloads of this method
        #  but should expect this override should always work?
        ...

    @abstractmethod
    def create(self, *, mode: int = 0o777, parents: bool = True, exist_ok: bool = True) -> None:
        """Materialise folder representation to directories on disk.
        Subclass may opt to populate child folders eagerly.
        # TODO think about these semantics more deeply

        Variant on Pathlib.mkdir() with more sensible defaults for static folders context"""
