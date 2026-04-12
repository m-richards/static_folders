# Changelog

## Development Version
- Subfolder attributes with a pre-assigned `Folder` value (used to give a custom
  directory name) are now correctly anchored under the parent folder (#13).
- `FolderLike` is now an Abstract Base Class (ABC) instead of a `typing.Protocol`.
  Subclasses must implement `from_path`, `__fspath__`, `get_subfolder`, and `create`.
- Now raise a `TypeError` when a `FolderLike`-annotated attribute is assigned a `Path` value.
- Now raise a `TypeError` when `FolderPartition` is constructed without an explicit generic type.

## Version 0.3 (August 23, 2025)
- Prevent str annotation to avoid ambiguity (#10)

## Version 0.2 (June 29, 2025)
- Add FolderPartition and EnumeratedFolderPartition classes (#4, #7)
- Make Folder root class slotted (#6)

## Version 0.1 - 0.1.3
- Initial version on PyPI with concept