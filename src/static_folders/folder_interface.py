from typing_extensions import Protocol, Self, Type, TypeVar, runtime_checkable

T = TypeVar("T")
from pathlib import Path


@runtime_checkable
class FolderLike(Protocol[T]):
    location: Path

    @classmethod
    def from_string(cls, path: str) -> Self:
        """Alternate constructor from string (for discoverability"""
        ...

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
