import os
import re
from pathlib import Path
from typing import ClassVar

import pytest
from attrs import define
from static_folders import Folder, FolderPartition
from static_folders.partitioned_folder import EnumeratedFolderPartition
import static_folders as sf


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
    tmp_path = Path("test")  # needs to not be "." or there's a soundness issue around deferred

    class PhotoYearFolder(Folder):
        index: Path = Path("index.md")

    class Photos(Folder):
        temp: Folder
        y2024: PhotoYearFolder
        y2025: PhotoYearFolder = sf.custom_name(
            "2025", annotation_type=PhotoYearFolder
        )  # provide concrete which doesn't have y prefix
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
        attrib = lambda x: print(x)  # noqa:E731

    class B(Folder):
        class Nested(Folder):
            attrib = lambda x: print(x)  # noqa:E731

        subfolder: A = sf.custom_name("custom_name_not_subfolder", annotation_type=A)

        readme: Path = Path("readme.txt")

    A(tmp_path)
    B(tmp_path)


class AsgsYearDir(Folder):
    """Test / example class."""

    sa1: Path = Path("SA1.gpkg")
    sa2: Path = Path("SA2.gpkg")


class AsgsLayersByYear(FolderPartition[AsgsYearDir]):
    pass


def test_partitioned_folder(path_not_on_disk: Path) -> None:
    f = AsgsLayersByYear(path_not_on_disk, partition_class=AsgsYearDir)
    y2016_dir_subfolder = f.get_subfolder("2016")
    assert not isinstance(y2016_dir_subfolder, AsgsYearDir)
    y2016_dir = f.get_partition("2016")
    assert isinstance(y2016_dir, AsgsYearDir)
    assert y2016_dir.sa1 == path_not_on_disk / "2016" / "SA1.gpkg"

    # check/ document IO behaviour
    assert not f.to_path().exists()
    assert not y2016_dir.sa1.exists()
    f.create()
    assert f.to_path().is_dir()
    # child under partition can't be materialised
    assert not y2016_dir.sa1.exists()


def test_enumerated_partitioned_folder(path_not_on_disk: Path) -> None:
    # repeat test with EnumeratedFolderPartition

    class EnumeratedAsgsLayersByYear(EnumeratedFolderPartition[AsgsYearDir]):
        partition_names = ("2016", "2021")

    f = EnumeratedAsgsLayersByYear(path_not_on_disk, partition_class=AsgsYearDir)
    y2016_dir_subfolder = f.get_subfolder("2016")
    assert not isinstance(y2016_dir_subfolder, AsgsYearDir)
    y2016_dir = f.get_partition("2016")
    assert isinstance(y2016_dir, AsgsYearDir)
    assert y2016_dir.sa1 == path_not_on_disk / "2016" / "SA1.gpkg"

    # check/ document IO behaviour
    assert not f.to_path().exists()
    assert not y2016_dir.sa1.exists()
    f.create()
    assert f.to_path().is_dir()
    # listed child under partition can be materialised
    assert y2016_dir.to_path().is_dir()
    assert f.get_subfolder("2021").to_path().exists()
    assert not f.get_subfolder("2023").to_path().exists()
    with pytest.raises(NameError):
        f.get_partition("2023")


def test_prefixed_enumerated_partitioned_folder(path_not_on_disk: Path) -> None:
    # repeat test with EnumeratedFolderPartition

    class EnumeratedAsgsLayersByYear(EnumeratedFolderPartition[AsgsYearDir]):
        partition_prefix = "year="
        partition_names = ("2016", "2021")

    f = EnumeratedAsgsLayersByYear(path_not_on_disk, partition_class=AsgsYearDir)
    y2016_dir_subfolder = f.get_subfolder("year=2016")  # conforms but wrong method
    assert not isinstance(y2016_dir_subfolder, AsgsYearDir)
    y2016_dir = f.get_partition("year=2016")  # explicit prefix
    assert y2016_dir.sa1 == path_not_on_disk / "year=2016" / "SA1.gpkg"
    y2016_dir2 = f.get_partition("2016")  # implicit prefix
    assert y2016_dir == y2016_dir2  # attrs equality implies equal
    assert y2016_dir != y2016_dir_subfolder
    assert isinstance(y2016_dir2, AsgsYearDir)
    assert y2016_dir2.sa1 == path_not_on_disk / "year=2016" / "SA1.gpkg"

    # check/ document IO behaviour
    assert not f.to_path().exists()
    assert not y2016_dir.sa1.exists()
    f.create()
    assert f.to_path().is_dir()
    # listed child under partition can be materialised
    assert y2016_dir.to_path().is_dir()
    assert f.get_subfolder("year=2021").to_path().exists()
    assert not f.get_subfolder("year=2023").to_path().exists()
    with pytest.raises(NameError):
        f.get_partition("year=2023")


def test_enumerated_subfolder_logical(path_not_on_disk: Path) -> None:
    class EnumeratedAsgsLayersByYear(EnumeratedFolderPartition[AsgsYearDir]):
        partition_prefix = "year="
        partition_names = ("2016", "2021")

    f = EnumeratedAsgsLayersByYear(path_not_on_disk, partition_class=AsgsYearDir)

    assert type(f.get_subfolder("foo")) == Folder  # Shouldn't be AsgsYearDir, doesn't conform # noqa: E721
    assert type(f.get_subfolder("foo", subfolder_class=AsgsYearDir)) == AsgsYearDir  # noqa: E721
    assert type(f.get_partition("2016")) == AsgsYearDir  # noqa: E721


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
    # If we had an api based around decorators, this wouldn't come up
    class Custom(Folder):
        def __attrs_post_init__(self) -> None:
            pass

    a = Custom(path_not_on_disk)
    a.get_subfolder("foo")


def test_custom_folder_names(path_not_on_disk: Path) -> None:
    class Custom(Folder):
        a: Folder
        b: Folder = sf.custom_name("02_b", annotation_type=Folder)
        c: AsgsYearDir = sf.custom_name("02_c", annotation_type=AsgsYearDir)

    folder = Custom(path_not_on_disk)
    assert isinstance(folder.a, Folder)
    assert folder.a.to_path() == path_not_on_disk / "a"
    assert folder.b.to_path() == path_not_on_disk / "02_b"


def test_ambiguous_annotations_error_out(path_not_on_disk: Path) -> None:
    class Custom(Folder):
        a: Folder = Path("foo.txt")  # type:ignore[assignment]

    with pytest.raises(
        TypeError,
        match=re.escape("Annotating an attribute with a FolderLike type and a Path value is ambiguous and not supported"),
    ):
        Custom(path_not_on_disk)


def test_eager_folder_default_errors(path_not_on_disk: Path) -> None:
    class Custom(Folder):
        a: Folder = Folder("foo")

    with pytest.raises(
        TypeError,
        match=re.escape("Providing a FolderLike annotation with a FolderLike value ") + ".*" + re.escape(" is deprecated"),
    ):
        Custom(path_not_on_disk)

def test_eager_folder_default_errors_folder_partition(path_not_on_disk: Path) -> None:
    class Custom2(Folder):
        a: FolderPartition = FolderPartition("foo", partition_class=Folder)

    with pytest.raises(
        TypeError,
        match=re.escape("Providing a FolderLike annotation with a FolderLike value ") + ".*" + re.escape(" is deprecated"),
    ):
        Custom2(path_not_on_disk)
