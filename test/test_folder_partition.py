from pathlib import Path

import pytest
from test_basic import AsgsYearDir

from static_folders import EnumeratedFolderPartition, Folder, FolderPartition


@pytest.fixture
def path_not_on_disk(tmp_path: Path) -> Path:
    # get a path which pytest isn't mkdiring
    return tmp_path / "new_dir_not_on_disk"


class AsgsLayersByYear(FolderPartition[AsgsYearDir]):
    pass


def test_partitioned_folder(path_not_on_disk: Path) -> None:
    f = AsgsLayersByYear(path_not_on_disk)
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

    f = EnumeratedAsgsLayersByYear(path_not_on_disk)
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

    f = EnumeratedAsgsLayersByYear(path_not_on_disk)
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

    f = EnumeratedAsgsLayersByYear(path_not_on_disk)

    assert type(f.get_subfolder("foo")) == Folder  # Shouldn't be AsgsYearDir, doesn't conform # noqa: E721
    assert type(f.get_subfolder("foo", subfolder_class=AsgsYearDir)) == AsgsYearDir  # noqa: E721
    assert type(f.get_partition("2016")) == AsgsYearDir  # noqa: E721


def test_folder_partition_class_getitem_caching(path_not_on_disk: Path) -> None:
    # FolderPartition[X] must return the same class object on repeated calls.
    assert FolderPartition[AsgsYearDir] is FolderPartition[AsgsYearDir]

    class MultiPartition(Folder):
        parts_a: FolderPartition[AsgsYearDir]
        parts_b: FolderPartition[AsgsYearDir]

    folder = MultiPartition(path_not_on_disk)
    assert type(folder.parts_a) is type(folder.parts_b)
