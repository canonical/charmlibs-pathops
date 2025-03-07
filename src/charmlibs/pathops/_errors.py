# Copyright 2025 Canonical Ltd.
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

"""Methods for matching Python Exceptions to Pebble Errors and creating Exception objects."""

from __future__ import annotations

import errno
import os

from ops import pebble


class DirectoryNotEmpty:
    @staticmethod
    def matches(error: pebble.Error) -> bool:
        return False

    @staticmethod
    def exception(msg: str) -> OSError:
        return OSError(errno.ENOTEMPTY, os.strerror(errno.ENOTEMPTY), msg)


class FileExists:
    @staticmethod
    def matches(error: pebble.Error) -> bool:
        return (
            isinstance(error, pebble.PathError)
            and error.kind == 'generic-file-error'
            and 'file exists' in error.message
        )

    @staticmethod
    def exception(msg: str) -> FileExistsError:
        return FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), msg)


class FileNotFound:
    @staticmethod
    def matches(error: pebble.Error) -> bool:
        return (isinstance(error, pebble.APIError) and error.code == 404) or (
            isinstance(error, pebble.PathError) and error.kind == 'not-found'
        )

    @staticmethod
    def exception(msg: str) -> FileNotFoundError:
        # pebble will return this error when trying to read_{text,bytes} a socket
        # pathlib raises OSError(errno.ENXIO, os.strerror(errno.ENXIO), path) in this case
        # displaying as "OSError: [Errno 6] No such device or address: '/path'"
        # since FileNotFoundError is a subtype of OSError, and this case should be rare
        # it seems sensible to just raise FileNotFoundError here, without checking
        # if the file in question is a socket
        return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), msg)


class IsADirectory:
    @staticmethod
    def matches(error: pebble.Error) -> bool:
        return (
            isinstance(error, pebble.PathError)
            and error.kind == 'generic-file-error'
            and 'can only read a regular file' in error.message
        )

    @staticmethod
    def exception(msg: str) -> IsADirectoryError:
        return IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), msg)


class NotADirectory:
    @staticmethod
    def exception(msg: str) -> NotADirectoryError:
        return NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), msg)


class Permission:
    @classmethod
    def matches(cls, error: pebble.Error) -> bool:
        return isinstance(error, pebble.PathError) and error.kind == 'permission-denied'

    @staticmethod
    def exception(msg: str) -> PermissionError:
        return PermissionError(errno.EPERM, os.strerror(errno.EPERM), msg)
