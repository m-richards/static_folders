import os
import re
from pathlib import Path

import pytest
from attrs import define
from static_folders import Folder, FolderPartition
from static_folders.partitioned_folder import EnumeratedFolderPartition


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


def test_missing_type_annotation(tmp_path):
    # Footgun here that if file is not annotated, we don't re-write
    @define
    class SubFolder(Folder):
        file = Path("file.txt")

    with pytest.raises(
        TypeError,
        match=re.escape("Folder subclasses do not support Folder or Path type fields without type annotations"),
    ):
        SubFolder(tmp_path)


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
    tmp_path = Path(".")

    class PhotoYearFolder(Folder):
        index: Path = Path("index.md")

    class Photos(Folder):
        temp: Folder
        y2024: PhotoYearFolder
        y2025: PhotoYearFolder = PhotoYearFolder(Path("2025"))  # provide concrete which doesn't have y prefix
        y2026: PhotoYearFolder = PhotoYearFolder("2026")  # string arg is fine too
        readme: Path = Path("readme.md")

    photos = Photos(tmp_path)
    assert isinstance(photos.readme, Path)
    assert isinstance(photos.temp, Folder)
    assert isinstance(photos.y2024, PhotoYearFolder)

    assert photos.readme == tmp_path / "readme.md"
    assert photos.y2024.index == tmp_path / "y2024" / "index.md"
    assert photos.y2025.index == tmp_path / "2025" / "index.md"
    assert photos.y2026.index == tmp_path / "2026" / "index.md"
    child_folder2 = photos.get_subfolder("2026", subfolder_class=PhotoYearFolder)
    child_folder2a = photos.get_subfolder("2026", subfolder_class=Folder)
    assert isinstance(child_folder2, PhotoYearFolder)
    assert isinstance(child_folder2a, Folder) and not isinstance(child_folder2a, PhotoYearFolder)  # noqa: PT018


def test_exotic_attributes_okay(tmp_path: Path) -> None:
    class A(Folder):
        attrib = lambda x: print(x)  # noqa:E731

    class B(Folder):
        class Nested(Folder):
            attrib = lambda x: print(x)  # noqa:E731

        readme: Path = Path("readme.txt")

    A(tmp_path)
    B(tmp_path)


class AsgsYearDir(Folder):
    """Test / example class."""

    sa1: Path = Path("SA1.gpkg")
    sa2: Path = Path("SA2.gpkg")


class AsgsLayersByYear(FolderPartition[AsgsYearDir]):
    pass


def test_partitioned_folder(tmp_path: Path) -> None:
    root_dir = tmp_path / "new_dir_not_on_disk"

    f = AsgsLayersByYear(root_dir, partition_class=AsgsYearDir)
    y2016_dir = f.get_subfolder("2016")
    assert isinstance(y2016_dir, AsgsYearDir)
    assert y2016_dir.sa1 == root_dir / "2016" / "SA1.gpkg"

    # check/ document IO behaviour
    assert not f.to_path().exists()
    assert not y2016_dir.sa1.exists()
    f.create()
    assert f.to_path().is_dir()
    # child under partition can't be materialised
    assert not y2016_dir.sa1.exists()


def test_enumerated_partitioned_folder(tmp_path: Path) -> None:
    # repeat test with EnumeratedFolderPartition

    class EnumeratedAsgsLayersByYear(EnumeratedFolderPartition[AsgsYearDir]):
        partition_names = ["2016", "2021"]

    root_dir = tmp_path / "new_dir_not_on_disk"

    f = EnumeratedAsgsLayersByYear(root_dir, partition_class=AsgsYearDir)
    y2016_dir = f.get_subfolder("2016")
    assert isinstance(y2016_dir, AsgsYearDir)
    assert y2016_dir.sa1 == root_dir / "2016" / "SA1.gpkg"

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
