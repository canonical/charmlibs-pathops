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

"""Implementation of ContainerPath class."""

from __future__ import annotations

import errno
import pathlib
import re
import typing

from ops import pebble

from . import _constants, _errors, _fileinfo

if typing.TYPE_CHECKING:
    from typing import Generator, Literal

    import ops
    from typing_extensions import Self

    from ._types import Bytes, StrPathLike


class RelativePathError(ValueError):
    """ContainerPath only supports absolute paths.

    This is because Pebble only works with absolute paths. Relative path support
    will likely remain unavailable at least until Pebble supports relative paths.
    In the meantime, use absolute paths.
    """


class ContainerPath:
    def __init__(self, *parts: StrPathLike, container: ops.Container) -> None:
        self._container = container
        self._path = pathlib.PurePosixPath(*parts)
        if not self._path.is_absolute():
            raise RelativePathError(
                f'ContainerPath arguments resolve to relative path: {self._path}'
            )

    def _description(self) -> str:
        return f"'{self._path}' in ops.Container {self._container.name!r}"

    #############################
    # protocol PurePath methods #
    #############################

    def __hash__(self) -> int:
        return hash((self._container.name, self._path))

    def __repr__(self) -> str:
        # TODO: eval'able representation -- requires a way to go from container name to container
        return f'{type(self).__name__}({self._path}, container={self._container})'

    def __str__(self) -> str:
        return self._path.__str__()

    def as_posix(self) -> str:
        return self._path.__str__()

    def __lt__(self, other: Self) -> bool:
        if not self._can_compare(other):
            return NotImplemented
        return self._path < other._path

    def __le__(self, other: Self) -> bool:
        if not self._can_compare(other):
            return NotImplemented
        return self._path <= other._path

    def __gt__(self, other: Self) -> bool:
        if not self._can_compare(other):
            return NotImplemented
        return self._path > other._path

    def __ge__(self, other: Self) -> bool:
        if not self._can_compare(other):
            return NotImplemented
        return self._path >= other._path

    def _can_compare(self, other: object) -> bool:
        return isinstance(other, ContainerPath) and other._container.name == self._container.name

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, ContainerPath) or self._container.name != other._container.name:
            return False
        return self._path == other._path

    def __truediv__(self, key: StrPathLike) -> Self:
        """Return a new ContainerPath with the same container and the joined path.

        The joined path is equivalent to str(self) / pathlib.PurePath(key).

        Note that the right hand operand here cannot be a ContainerPath.
        This is because ContainerPath objects only support absolute paths currently,
        so using one as the right hand side is likely to be an error.
        For the same reason, __rtruediv__ is undefined, meaning a ContainerPath cannot
        be the right hand side operand for arbitrary string or PathLike objects either.
        """
        return self.with_segments(self._path, key)

    def is_absolute(self) -> bool:
        """Whether the path is absolute. Will always be True, as relative paths error on init."""
        return self._path.is_absolute()

    def match(self, path_pattern: str) -> bool:
        """Whether the patch matches the given pattern.

        If the pattern is relative, matching is done from the right, otherwise the
        entire path is matched. The recursive wildcard '**' is not supported.
        """
        return self._path.match(path_pattern)

    def with_name(self, name: str) -> Self:
        """Return a new ContainerPath with the same container and the filename changed."""
        return self.with_segments(self._path.with_name(name))

    def with_suffix(self, suffix: str) -> Self:
        """Return a new ContainerPath with the same container and the suffix changed.

        If the original path had no suffix, the new suffix is added.
        The new suffix must start with '.', unless the new suffix is an empty string,
        in which case the original suffix (if there was one) is removed ('.' included).
        """
        return self.with_segments(self._path.with_suffix(suffix))

    def joinpath(self, *other: StrPathLike) -> Self:
        """Return a new ContainerPath with the same container and the new args joined to its path.

        Args:
            other: Any number of path-like objects or strs. Note -- ContainerPath is not path-like.
                If zero are provided, an effective copy of this ContainerPath object is returned.
                *other is joined to this object's path as with os.path.join. This means that if
                any member of other is an absolute path, all the previous components, including
                this object's path, are dropped entirely.
        """
        return self.with_segments(self._path, *other)

    @property
    def parents(self) -> tuple[Self, ...]:
        return tuple(self.with_segments(p) for p in self._path.parents)

    @property
    def parent(self) -> Self:
        return self.with_segments(self._path.parent)

    @property
    def parts(self) -> tuple[str, ...]:
        return self._path.parts

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def suffix(self) -> str:
        return self._path.suffix

    @property
    def suffixes(self) -> list[str]:
        return self._path.suffixes

    @property
    def stem(self) -> str:
        return self._path.stem

    #########################
    # protocol Path methods #
    #########################

    def read_text(
        self,
        *,
        newline: str | None = None,  # 3.13+
        # None -> treat \n \r \r\n as newlines, convert to \n
        # ''   -> treat \n \r \r\n as newlines, return unmodified
        # (\n, \r, \r\n) -> only treat that option as a newline, return unmodified
        # since this method doesn't readlines or anything, the only difference is the return value
        # i.e. None -> convert to \n; any other value -> return unmodified
    ) -> str:
        text = self._pull(text=True)
        if newline is None:
            return re.sub('\r\n|\r|\n', '\n', text)
        return text

    def read_bytes(self) -> bytes:
        return self._pull(text=False)

    @typing.overload
    def _pull(self, *, text: Literal[True]) -> str: ...
    @typing.overload
    def _pull(self, *, text: Literal[False] = False) -> bytes: ...
    def _pull(self, *, text: bool = False):
        encoding = 'utf-8' if text else None
        try:
            with self._container.pull(self._path, encoding=encoding) as f:
                return f.read()
        except pebble.PathError as e:
            description = self._description()
            _errors.raise_if_matches_file_not_found(e, msg=description)
            _errors.raise_if_matches_is_a_directory(e, msg=description)
            _errors.raise_if_matches_permission(e, msg=description)
            raise

    def iterdir(self) -> typing.Generator[Self]:
        # python < 3.13 defers NotADirectoryError to iteration time, but python 3.13 raises on call
        # for future proofing we will check on call
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        if info.type != pebble.FileType.DIRECTORY:
            _errors.raise_not_a_directory(self._description())
        file_infos = self._container.list_files(self._path)
        for f in file_infos:
            yield self.with_segments(f.path)

    def glob(
        self,
        pattern: StrPathLike,  # support for _StrPath added in 3.13 (was str only before)
        # *,
        # case_sensitive: bool = False,  # added in 3.12
        # recurse_symlinks: bool = False,  # added in 3.13
    ) -> Generator[Self]:
        if not isinstance(pattern, str):
            pattern = str(pattern)
        *pattern_parents, pattern_itself = pathlib.PurePath(pattern).parts
        if '**' in pattern_parents:
            raise NotImplementedError('Recursive glob is not supported.')
        if '**' in pattern:
            raise ValueError("Invalid pattern: '**' can only be an entire path component")
        if not pattern_parents:
            file_infos = self._container.list_files(self._path, pattern=pattern_itself)
            for f in file_infos:
                yield self.with_segments(f.path)
            return
        first, *rest = pattern_parents
        next_pattern = pathlib.PurePath(*rest, pattern_itself)
        if first == '*':
            for container_path in self.iterdir():
                if container_path.is_dir():
                    yield from container_path.glob(next_pattern)
        else:
            assert '*' not in first
            yield from (self / first).glob(next_pattern)

    def owner(self) -> str:
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        return info.user or ''

    def group(self) -> str:
        info = _fileinfo.from_container_path(self)  # FileNotFoundError if path doesn't exist
        return info.group or ''

    def exists(self) -> bool:
        return self._exists_and_matches(filetype=None)

    def is_dir(self) -> bool:
        return self._exists_and_matches(pebble.FileType.DIRECTORY)

    def is_file(self) -> bool:
        return self._exists_and_matches(pebble.FileType.FILE)

    def is_fifo(self) -> bool:
        return self._exists_and_matches(pebble.FileType.NAMED_PIPE)

    def is_socket(self) -> bool:
        return self._exists_and_matches(pebble.FileType.SOCKET)

    def _exists_and_matches(self, filetype: pebble.FileType | None) -> bool:
        try:
            info = _fileinfo.from_container_path(self)
        except FileNotFoundError:
            return False
        except OSError as e:
            if e.errno == errno.ELOOP:
                return False  # too many levels of symbolic links
            raise
        if filetype is None:  # we only care if the file exists
            return True
        return info.type is filetype

    ##################################################
    # protocol Path methods with extended signatures #
    ##################################################

    def write_bytes(
        self,
        data: Bytes,
        # extended with chmod + chown args
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        if isinstance(data, (bytearray, memoryview)):
            # TODO: update ops to correctly test for bytearray and memoryview in push
            data = bytes(data)
        try:
            self._container.push(
                path=self._path,
                source=data,
                make_dirs=False,
                permissions=mode,
                user=user if isinstance(user, str) else None,
                group=group if isinstance(group, str) else None,
            )
        except pebble.PathError as e:
            _errors.raise_if_matches_lookup(e, msg=e.message)
            description = self._description()
            _errors.raise_if_matches_file_not_found(e, msg=description)
            _errors.raise_if_matches_permission(e, msg=description)
            raise
        return len(data)

    def write_text(
        self,
        data: str,
        # encoding: str | None = None,
        # errors: typing.Literal['strict', 'ignore'] | None = None,
        # newline: typing.Literal['', '\n', '\r', '\r\n'] | None = None,  # 3.10+
        # extended with chmod + chown args
        *,
        mode: int = _constants.DEFAULT_WRITE_MODE,
        user: str | None = None,
        group: str | None = None,
    ) -> int:
        # if encoding is None:
        #     encoding = 'utf-8'
        # if errors is None:
        #     errors = 'strict'
        # if newline in ('\r', '\r\n'):
        #     data = re.sub('\n', newline, data)
        # # else newline in (None, '', '\n') and we do nothing, assuming os.linesep == '\n'
        encoding = 'utf-8'
        errors = 'strict'
        encoded_data = bytes(data, encoding=encoding, errors=errors)
        return self.write_bytes(encoded_data, mode=mode, user=user, group=group)

    def mkdir(
        self,
        mode: int = _constants.DEFAULT_MKDIR_MODE,
        parents: bool = False,
        exist_ok: bool = False,
        # extended with chown args
        *,
        user: str | None = None,
        group: str | None = None,
    ) -> None:
        # only make an extra pebble call if parents xor exist_ok
        # if both are true or both are false we can just let pebble's make_parents handle it
        if parents and not exist_ok and self.exists():
            raise _errors.raise_file_exists(self._description())
        elif exist_ok and not parents and not self.parent.exists():
            _errors.raise_file_not_found(self.parent._description())
        try:
            self._container.make_dir(
                path=self._path,
                make_parents=parents or exist_ok,  # see validation above
                permissions=mode,
                user=user if isinstance(user, str) else None,
                group=group if isinstance(group, str) else None,
            )
        except pebble.PathError as e:
            _errors.raise_if_matches_lookup(e, msg=e.message)
            description = self._description()
            if _errors.matches_not_a_directory(e):
                # target exists and isn't a directory, or parent isn't a directory
                if not self.parent.is_dir():
                    _errors.raise_not_a_directory(msg=description, from_=e)
                _errors.raise_file_exists(self._description(), from_=e)
            _errors.raise_if_matches_file_exists(e, msg=description)
            _errors.raise_if_matches_file_not_found(e, msg=description)
            _errors.raise_if_matches_permission(e, msg=description)
            raise

    #############################
    # non-protocol Path methods #
    #############################

    def with_segments(self, *pathsegments: StrPathLike) -> Self:
        return type(self)(*pathsegments, container=self._container)
