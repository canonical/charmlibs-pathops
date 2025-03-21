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

r""":mod:`pathlib`-like interface for local and :class:`ops.Container` filesystem paths.

:class:`ContainerPath` implements a ``pathlib.Path`` style interface for path operations on
a Juju charm's workload container.
This interface is defined in :class:`PathProtocol`, which defines a subset of ``pathlib.Path``
methods that can be implemented via Pebble. The file creation methods are extended with ownership
and permissions arguments, as Pebble sets these on file creation.
:class:`LocalPath` is a subclass of ``pathlib.Path`` that provides these extended method
signatures for local filesystem operations.

.. tip::
    When writing substrate-agnostic code, use :class:`PathProtocol` in your type annotations,
    for accurate type checking and useful autocompletions.
    Calling code can then supply a :class:`ContainerPath` or :class:`LocalPath` as needed.

.. warning::
    :class:`ContainerPath` may raise a :class:`PebbleConnectionError` if the workload container is
    unreachable. Subtrate-agnostic code may choose to be aware of this, or may leave handling this
    up to substrate-aware calling code, documenting this if so.

This library also provides the following functions:

- :func:`ensure_contents` operates on a :class:`ContainerPath` or any local filesystem :class:`str`
  or :class:`os.PathLike` object, and ensures that the requested contents are available at that
  path, writing and setting ownership and permissions as needed.

.. note::
    ``StrPathLike`` is a type alias for :class:`str` | :class:`os.PathLike`\[:class:`str`].
    This allows path arguments to be specified as strings or as path-like objects, such as
    :class:`pathlib.PurePath`. :class:`ContainerPath` is **not** :class:`os.PathLike`.
"""

from __future__ import annotations

from pathlib import Path as _Path  # for __version__

from ops.pebble import ConnectionError as PebbleConnectionError

from ._container_path import ContainerPath, RelativePathError
from ._functions import ensure_contents
from ._local_path import LocalPath
from ._types import PathProtocol

__all__ = (
    'ContainerPath',
    'LocalPath',
    'PathProtocol',
    'PebbleConnectionError',
    'RelativePathError',
    'ensure_contents',
)

__version__ = (_Path(__file__).parent / '_version.txt').read_text()
