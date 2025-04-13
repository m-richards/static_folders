import os
from pathlib import Path

from static_folders import Folder


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


# def staticfolder(cls):
#     annotations = inspect.get_annotations(cls)
#     print(cls, annotations)
#
#     for k,v in annotations.items():
#         if isinstance(v, Folder):
#             cls.k = Folder()
#
# # @staticfolder
#
# class TestFolder(Folder):
#     item: Path = Path("foo.txt")
#
# class RepoFolder(Folder):
#     child: TestFolder
#     path: Path = Path("out.txt")
#     # path2: Path = "out.txt" # arguably could be supported but might confuse mypy
#     # just here for legibility
#
#
# r = RepoFolder(Path("foo"))
# print(r)
# print(r.child)
# print(r.path)
#
#
#
# r.child.item
# reveal_type(r.child.item)
# reveal_type(r.child)
#
# from attrs import asdict, define, make_class, Factory
