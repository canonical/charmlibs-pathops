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

"""Integration tests using a real Juju and charm to test ContainerPath."""

from __future__ import annotations

import ast
import typing

import pytest

if typing.TYPE_CHECKING:
    import jubilant


def test_deploy(juju: jubilant.Juju, charm: str):
    """The deployment takes place in the module scoped `juju` fixture."""
    assert charm in juju.status().apps


def test_ensure_contents(juju: jubilant.Juju, charm: str):
    contents = 'Hello world!'
    result = juju.run(
        f'{charm}/0', 'ensure-contents', params={'path': 'file.txt', 'contents': contents}
    )
    assert result.results['contents'] == contents


def test_iterdir(juju: jubilant.Juju, charm: str):
    n = 2
    result = juju.run(f'{charm}/0', 'iterdir', params={'n-temp-files': n})
    files = ast.literal_eval(result.results['files'])
    assert len(files) == n


@pytest.mark.parametrize(
    ('user', 'group'),
    (
        (None, None),
        ('root', None),
        (None, 'root'),
        ('root', 'root'),
    ),
)
@pytest.mark.parametrize('method', ['mkdir', 'write_bytes', 'write_text'])
def test_chown(juju: jubilant.Juju, charm: str, method: str, user: str | None, group: str | None):
    print('juju run')
    result = juju.run(
        f'{charm}/0',
        'chown',
        params={'method': method, 'user': user or '', 'group': group or ''},
    )
    print(result)
    print(result.results)
    if user is not None:
        print('asserting on user')
        assert result.results['user'] == user
    if group is not None:
        print('asserting on group')
        assert result.results['group'] == group
