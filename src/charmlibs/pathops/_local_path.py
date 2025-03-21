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

"""Implementation of LocalPath class."""

from __future__ import annotations

import grp
import pathlib
import pwd
import shutil
import typing

from . import _constants

if typing.TYPE_CHECKING:
    from typing_extensions import Buffer


class LocalPath(pathlib.PosixPath):
    r""":class:`pathlib.PosixPath` subclass with extended file-creation method arguments.

    .. note::
        The :meth:`write_bytes`, :meth:`write_text`, and :meth:`mkdir` methods are extended with
        file permission and ownership arguments, for compatibility with :class:`PathProtocol`.

    Args:
        \*parts: :class:`str` or :class:`os.PathLike`. ``LocalPath`` takes no keyword arguments.

    ::

        LocalPath(pathlib.Path('/foo'))
        LocalPath('/', 'foo')
    """

    def write_bytes(
        self,
        data: Buffer,
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        """Write the provided data to the corresponding local filesystem path.

        .. note::
            Compared to :meth:`pathlib.Path.write_bytes`, this method adds ``mode``, ``user``
            and ``group`` args. These are used to set the permissions and ownership of the file.

        Args:
            data: The bytes to write, typically a :class:`bytes` object, but may also be a
                :class:`bytearray` or :class:`memoryview`.
            mode: The permissions to set on the file using :meth:`pathlib.PosixPath.chmod`.
            user: The name of the user to set for the file using :func:`shutil.chown`.
                Validated to be an existing user before writing.
            group: The name of the group to set for the file using :func:`shutil.chown`.
                Validated to be an existing group before writing.

        Returns: The number of bytes written.

        Raises:
            FileNotFoundError: if the parent directory does not exist.
            LookupError: if the user or group is unknown.
            NotADirectoryError: if the parent exists as a non-directory file.
            PermissionError: if the local user does not have permissions for the operation.
        """
        _validate_user_and_group(user=user, group=group)
        bytes_written = super().write_bytes(data)
        _chown_if_needed(self, user=user, group=group)
        self.chmod(mode)
        return bytes_written

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        # TODO: support Python 3.10+ newline argument
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        """Write the provided string to the corresponding local filesystem path.

        .. note::
            Compared to :meth:`pathlib.Path.write_bytes`, this method adds ``mode``, ``user``
            and ``group`` args. These are used to set the permissions and ownership of the file.

        .. warning::
            :class:`ContainerPath` and :class:`PathProtocol` do not support the
            ``encoding`` and ``errors`` arguments of :meth:`pathlib.Path.write_text`.
            For :class:`ContainerPath` compatible code, do not use these arguments.
            They are provided to allow :class:`LocalPath` to be used as a drop-in
            replacement for :class:`pathlib.Path` if needed.

        Args:
            data: The string to write. Newlines are not modified on writing.
            encoding: The encoding to use when writing the data, defaults to 'utf-8'.
            errors: 'strict' to raise any encoding errors, 'ignore' to ignore them.
                Defaults to 'strict'.
            mode: The permissions to set on the file using :meth:`pathlib.PosixPath.chmod`.
            user: The name of the user to set for the file using :func:`shutil.chown`.
                Validated to be an existing user before writing.
            group: The name of the group to set for the file using :func:`shutil.chown`.
                Validated to be an existing group before writing.

        Returns: The number of bytes written.

        Raises:
            FileNotFoundError: if the parent directory does not exist.
            LookupError: if the user or group is unknown.
            NotADirectoryError: if the parent exists as a non-directory file.
            PermissionError: if the local user does not have permissions for the operation.
        """
        _validate_user_and_group(user=user, group=group)
        bytes_written = super().write_text(data, encoding=encoding, errors=errors)
        _chown_if_needed(self, user=user, group=group)
        self.chmod(mode)
        return bytes_written

    def mkdir(
        self,
        mode: int = _constants.DEFAULT_MKDIR_MODE,
        parents: bool = False,
        exist_ok: bool = False,
        *,
        user: str | None = None,
        group: str | None = None,
    ) -> None:
        """Create a new directory at the corresponding local filesystem path.

        .. note::
            Compared to :meth:`pathlib.Path.mkdir`, this method adds ``user`` and ``group`` args.
            These are used to set the ownership of the created directory. Any created parents
            will not have their ownership set.

        Args:
            mode: The permissions to set on the created directory. Any parents created will have
                their permissions set to the default value for this argument.
            parents: Whether to create any missing parent directories as well. If ``False``
                (default) and a parent directory does not exist, a :class:`FileNotFound` error will
                be raised.
            exist_ok: Whether to error if the directory already exists. If ``False`` (default) and
                the directory already exists, a :class:`FileExistsError` will be raised.
            user: The name of the user to set for the directory using :func:`shutil.chown`.
                Validated to be an existing user before writing.
            group: The name of the group to set for the directory using :func:`shutil.chown`.
                Validated to be an existing group before writing.

        Raises:
            FileExistsError: if the directory already exists and ``exist_ok`` is ``False``.
            FileNotFoundError: if the parent directory does not exist and ``parents`` is ``False``.
            LookupError: if the user or group is unknown.
            NotADirectoryError: if the parent exists as a non-directory file.
            PermissionError: if the local user does not have permissions for the operation.
        """
        _validate_user_and_group(user=user, group=group)
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        _chown_if_needed(self, user=user, group=group)


def _validate_user_and_group(user: str | None, group: str | None):
    if user is not None:
        pwd.getpwnam(user)
    if group is not None:
        grp.getgrnam(group)


def _chown_if_needed(path: pathlib.Path, user: str | int | None, group: str | int | None) -> None:
    # shutil.chown is happy as long as either user or group is not None
    # but the type checker doesn't like that, so we have to be more explicit
    if user is not None and group is not None:
        shutil.chown(path, user=user, group=group)
    elif user is not None:
        shutil.chown(path, user=user)
    elif group is not None:
        shutil.chown(path, group=group)
