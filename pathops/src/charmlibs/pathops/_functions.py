# Copyright 2024 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Public helper functions exported by this package."""

from __future__ import annotations

import pathlib
import shutil
import typing

from ops import pebble

from . import _constants, _errors, _fileinfo
from ._container_path import ContainerPath
from ._local_path import LocalPath

if typing.TYPE_CHECKING:
    import os
    from typing import BinaryIO, TextIO

    from typing_extensions import TypeIs

    from ._types import PathProtocol


def ensure_contents(
    path: str | os.PathLike[str] | PathProtocol,
    source: bytes | str | BinaryIO | TextIO,
    *,
    mode: int = _constants.DEFAULT_WRITE_MODE,
    user: str | None = None,
    group: str | None = None,
) -> bool:
    """Ensure ``source`` can be read from ``path``. Return True if any changes were made.

    Ensure that ``path`` exists, contains ``source``, has the correct permissions (``mode``),
    and has the correct file ownership (``user`` and ``group``).

    Args:
        path: A local or remote filesystem path.
        source: The desired contents in ``str`` or ``bytes`` form, or an object with a ``.read()``
            method which returns a ``str`` or ``bytes`` object.
        mode: The desired file permissions.
        user: The desired file owner, or ``None`` to not change the owner.
        group: The desired group, or ``None`` to not change the group.

    Returns:
        ``True`` if any changes were made, including permissions or ownership, otherwise ``False``.

    Raises:
        LookupError: if the user or group is unknown.
        NotADirectoryError: if the parent exists as a non-directory file.
        PermissionError: if the user does not have permissions for the operation.
        :class:`PebbleConnectionError`: if the remote Pebble client cannot be reached.
    """
    if _is_str_pathlike(path):
        path = LocalPath(path)
    source = _as_bytes(source)
    try:
        info = _get_fileinfo(path)
    except FileNotFoundError:
        pass  # file doesn't exist, so writing is required
    else:  # check if metadata and contents already match
        if (
            (info.permissions == mode)
            and (user is None or info.user == user)
            and (group is None or info.group == group)
            and (path.read_bytes() == source)
        ):
            return False  # everything matches, so writing is not required
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source, mode=mode, user=user, group=group)
    return True


def _is_str_pathlike(obj: object) -> TypeIs[str | os.PathLike[str]]:
    return isinstance(obj, str) or hasattr(obj, '__fspath__')


def _get_fileinfo(path: str | os.PathLike[str] | PathProtocol) -> pebble.FileInfo:
    if isinstance(path, ContainerPath):
        return _fileinfo.from_container_path(path)
    assert _is_str_pathlike(path)
    return _fileinfo.from_pathlib_path(pathlib.Path(path))


def _as_bytes(source: bytes | str | BinaryIO | TextIO) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        return source.encode()
    return _as_bytes(source.read())


def remove_path(path: str | os.PathLike[str] | PathProtocol, *, recursive: bool = False) -> None:
    """Remove a file or directory following Pebble's file removal semantics.

    Args:
        path: The path to remove. If it is a non-empty directory, a :class:`DirectoryNotEmpty`
            error will be raised, unless ``recursive`` is ``True``.
        recursive: Whether to remove the contents of a non-empty directory ``path``.
            Also suppresses :class:`FileNotFoundError`.

    Raises:
        DirectoryNotEmpty: if ``path`` is a non-empty directory and ``recursive`` is ``False``.
        FileNotFoundError: if ``path`` does not exist and ``recursive`` is ``False``.
        PermissionError: if the Pebble user does not have permissions for the operation.
        PebbleConnectionError: if the remote Pebble client cannot be reached.
    """
    if isinstance(path, ContainerPath):
        return _remove_container_path(path, recursive=recursive)
    assert _is_str_pathlike(path)
    return _remove_pathlib_path(pathlib.Path(path), recursive=recursive)


def _remove_container_path(path: ContainerPath, recursive: bool) -> None:
    try:
        path._container.remove_path(path._path, recursive=recursive)
    except pebble.PathError as e:
        msg = repr(path)
        _errors.raise_if_matches_directory_not_empty(e, msg=msg)
        _errors.raise_if_matches_file_not_found(e, msg=msg)
        _errors.raise_if_matches_permission(e, msg=msg)
        raise


def _remove_pathlib_path(path: pathlib.Path, recursive: bool) -> None:
    if recursive and not path.exists():
        return
    if not path.is_dir():
        return path.unlink()
    if not recursive:
        return path.rmdir()
    shutil.rmtree(path)
