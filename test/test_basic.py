import os
import re
from pathlib import Path
from typing import ClassVar

import pytest
from attrs import define

from static_folders import Folder, FolderPartition


@pytest.fixture
def path_not_on_disk(tmp_path: Path) -> Path:
    # get a path which pytest isn't mkdiring
    return tmp_path / "new_dir_not_on_disk"


def test_basic(tmp_path: Path) -> None:
    f = Folder(tmp_path)
    assert f.to_path() == tmp_path
    assert os.fspath(f) == str(tmp_path)
    assert f.location == tmp_path
    assert f.get_file("foo.txt") == tmp_path / "foo.txt"
    assert f.to_path() / "foo.txt" == tmp_path / "foo.txt"
    child_folder = f.get_subfolder("out")
    assert isinstance(child_folder, Folder)
    assert child_folder.to_path() == tmp_path / "out"


def test_missing_type_annotation(tmp_path: Path) -> None:
    # Footgun here that if file is not annotated, we don't re-write
    @define
    class SubFolder(Folder):
        file = Path("file.txt")

    with pytest.raises(
        TypeError,
        match=re.escape("Folder subclasses do not support FolderLike or Path type fields without type annotations"),
    ):
        SubFolder(tmp_path)


def test_str_annotation_fails(tmp_path: Path) -> None:
    # Footgun on string annotations
    @define
    class SubFolder(Folder):
        file: str = "file.txt"

    with pytest.raises(
        TypeError,
        match=re.escape("Folder subclasses do not support raw str annotated fields, to avoid confusion"),
    ):
        SubFolder(tmp_path)


def test_classvar_str_works(tmp_path: Path) -> None:
    # Footgun on string annotations
    @define
    class SubFolder(Folder):
        file: ClassVar[str] = "file.txt"

    folder = SubFolder(tmp_path)
    assert folder.file == "file.txt"
    assert isinstance(folder.file, str)


def test_create(tmp_path: Path) -> None:
    class Nest2(Folder):
        nest: Folder
        file: Path = Path("file.txt")

    class Nest1(Folder):
        nest: Nest2

    root1 = tmp_path / "foo"
    n = Nest1(root1)
    assert not root1.exists()
    n.create()
    assert n.to_path().exists()
    assert root1.exists()
    assert n.nest.to_path().exists()
    assert n.nest.nest.to_path().exists()
    assert n.nest.nest.to_path().is_dir()
    # directory creation won't create dummy files
    assert not n.nest.file.is_file()


def test_nested(tmp_path: Path) -> None:
    # tmp_path cannot be ".", what would that mean when paths are resolved?

    class PhotoYearFolder(Folder):
        index: Path = Path("index.md")

    class Photos(Folder):
        temp: Folder
        y2024: PhotoYearFolder
        # provide concrete path which doesn't have y prefix
        y2025: PhotoYearFolder = PhotoYearFolder("2025")
        readme: Path = Path("readme.md")

    photos = Photos(tmp_path)
    assert isinstance(photos.readme, Path)
    assert isinstance(photos.temp, Folder)
    assert isinstance(photos.y2024, PhotoYearFolder)

    assert photos.readme == tmp_path / "readme.md"
    assert photos.y2024.index == tmp_path / "y2024" / "index.md"
    assert photos.y2025.index == tmp_path / "2025" / "index.md"
    assert photos.y2025.to_path() == tmp_path / "2025"
    child_folder2 = photos.get_subfolder("2025", subfolder_class=PhotoYearFolder)
    child_folder2a = photos.get_subfolder("2025", subfolder_class=Folder)
    assert isinstance(child_folder2, PhotoYearFolder)
    assert isinstance(child_folder2a, Folder) and not isinstance(child_folder2a, PhotoYearFolder)  # noqa: PT018


def test_exotic_attributes_okay(tmp_path: Path) -> None:
    class A(Folder):
        attrib = lambda x: print(x)  # noqa:E731, PLW0108

    class B(Folder):
        class Nested(Folder):
            attrib = lambda x: print(x)  # noqa:E731, PLW0108

        subfolder: A = A("custom_named_subfolder")

        readme: Path = Path("readme.txt")

    A(tmp_path)
    B(tmp_path)


class AsgsYearDir(Folder):
    """Test / example class."""

    sa1: Path = Path("SA1.gpkg")
    sa2: Path = Path("SA2.gpkg")


def test_attrs_subclass_post_init(path_not_on_disk: Path) -> None:
    # documenting that if we call super properly, this behaves properly.
    # but you need to call super!
    class Custom(Folder):
        def __attrs_post_init__(self) -> None:
            super().__attrs_post_init__()

    a = Custom(path_not_on_disk)
    a.get_subfolder("foo")


@pytest.mark.xfail(reason="if a user customises post init badly there's not much we can do.")
def test_attrs_subclass_post_init_missing(path_not_on_disk: Path) -> None:
    # documenting that if we call super properly, this behaves properly.
    # but you need to call super!
    class CustomWorking(Folder):
        def __attrs_post_init__(self) -> None:
            super().__attrs_post_init__()

    a = CustomWorking(path_not_on_disk)
    assert a.get_subfolder("foo") == path_not_on_disk / "foo"

    # If we had an api based around decorators, this wouldn't come up
    class Custom(Folder):
        def __attrs_post_init__(self) -> None:
            pass

    b = Custom(path_not_on_disk)
    b.get_subfolder("foo")


def test_custom_folder_names(path_not_on_disk: Path) -> None:
    # https://github.com/m-richards/static_folders/issues/11
    class Custom(Folder):
        a: Folder
        b: Folder = Folder("02_b")
        c: AsgsYearDir = AsgsYearDir("02_c")

    folder = Custom(path_not_on_disk)
    assert isinstance(folder.a, Folder)
    assert folder.a.to_path() == path_not_on_disk / "a"
    # this needs to be under path_not_on_disk, not a relative path to cwd
    assert folder.b.to_path() == path_not_on_disk / "02_b"
    assert folder.c.sa1 == path_not_on_disk / "02_c" / "SA1.gpkg"


def test_ambiguous_annotations_error_out(path_not_on_disk: Path) -> None:
    class Custom(Folder):
        a: Folder = Path("foo.txt")  # type:ignore[assignment]

    with pytest.raises(
        TypeError,
        match=re.escape("Annotating an attribute with a FolderLike type and a Path value is incorrect"),
    ):
        Custom(path_not_on_disk)


def test_folder_partition_generics_required(path_not_on_disk: Path) -> None:
    with pytest.raises(
        TypeError, match=re.escape("FolderPartition instance constructed without providing explicit generics")
    ):

        class _Custom2(Folder):
            a: FolderPartition = FolderPartition("foo")

    with pytest.raises(
        TypeError, match=re.escape("FolderPartition instance constructed without providing explicit generics")
    ):

        class _Custom3(Folder):
            a: FolderPartition[AsgsYearDir] = FolderPartition("foo")

    class _Custom4(Folder):
        a: FolderPartition = FolderPartition[AsgsYearDir]("foo")

    with pytest.raises(TypeError, match=re.escape("Building Class _Custom4 failed on constructing attribute")):
        # TODO this case fails at instantiation time, not class initialisation, that's annoying
        _Custom4(path_not_on_disk)

    # case which is permitted
    class _Custom5(AsgsYearDir):
        a: FolderPartition[AsgsYearDir]

    test = _Custom5(path_not_on_disk)
    assert test.a.get_partition("baz").sa1 == path_not_on_disk / "a" / "baz" / "SA1.gpkg"

    class _Custom6(AsgsYearDir):
        a: FolderPartition[AsgsYearDir] = FolderPartition[AsgsYearDir]("foo")

    test2 = _Custom6(path_not_on_disk)
    assert test2.a.get_partition("baz").sa1 == path_not_on_disk / "foo" / "baz" / "SA1.gpkg"
