from __future__ import annotations

import typing

from typing_extensions import Protocol, Type, TypeVar, runtime_checkable

if typing.TYPE_CHECKING:
    from pathlib import Path

T = TypeVar("T")


@runtime_checkable
class FolderLike(Protocol[T]):
    location: Path

    def __fspath__(self) -> str: ...

    def to_path(self) -> Path:
        # going to not follow the advice of https://hynek.me/articles/python-subclassing-redux/
        # since this should be the behaviour in all sane cases
        return self.location

    def get_file(self, name: str) -> Path:
        # going to not follow the advice of https://hynek.me/articles/python-subclassing-redux/
        # since this should be the behaviour in all sane cases
        return self.location / name

    def get_subfolder(self, name: str, subfolder_class: Type[T] = ...) -> T:
        # TODO is this a bad idea? we will have other @overloads of this method
        #  but should expect this override should always work?
        ...

    def create(self, *, mode: int = 0o777, parents: bool = True, exist_ok: bool = True) -> None:
        """Materialise folder representation to directories on disk.
        Subclass may opt to populate child folders eagerly.
        # TODO think about these semantics more deeply

        Variant on Pathlib.mkdir() with more sensible defaults for static folders context"""
