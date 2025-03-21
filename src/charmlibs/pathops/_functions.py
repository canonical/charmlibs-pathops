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
import typing

from . import _constants, _fileinfo
from ._container_path import ContainerPath
from ._local_path import LocalPath

if typing.TYPE_CHECKING:
    from typing import BinaryIO, TextIO

    from ops import pebble

    from ._types import StrPathLike


def ensure_contents(
    path: StrPathLike | ContainerPath,
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
        path: A :class:`str` or :class:`os.PathLike` local filesystem path, or a
            :class:`ContainerPath` remote filesystem path.
        source: The desired contents in ``str`` or ``bytes`` form, or an object with a ``.read()``
            method returning a ``str`` or ``bytes`` object.
        mode: The desired file permissions.
        user: The desired file owner, or ``None`` to not change the owner.
        group: The desired group, or ``None`` to not change the group.

    Returns:
        ``True`` if any changes were made, including permissions or ownership, otherwise ``False``.

    Raises:
        LookupError: if the user or group is unknown.
        NotADirectoryError: if the parent exists as a non-directory file.
        PermissionError: if the user does not have permissions for the operation.
        ops.pebble.ConnectionError: if the remote Pebble client cannot be reached.
    """
    if not isinstance(path, ContainerPath):  # most likely str or pathlib.Path
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


def _get_fileinfo(path: StrPathLike | ContainerPath) -> pebble.FileInfo:
    if isinstance(path, ContainerPath):
        return _fileinfo.from_container_path(path)
    return _fileinfo.from_pathlib_path(pathlib.Path(path))


def _as_bytes(source: bytes | str | BinaryIO | TextIO) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        return source.encode()
    return _as_bytes(source.read())
