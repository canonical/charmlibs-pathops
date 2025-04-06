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

"""Ensure that the test charms aren't out of sync."""

from __future__ import annotations

import pathlib

import yaml


def test_common_py():
    k = pathlib.Path(__file__).parent / 'charms' / 'kubernetes' / 'src' / 'common.py'
    m = pathlib.Path(__file__).parent / 'charms' / 'machine' / 'src' / 'common.py'
    assert k.read_text() == m.read_text()


def test_charmcraft_yaml():
    k = pathlib.Path(__file__).parent / 'charms' / 'kubernetes' / 'charmcraft.yaml'
    m = pathlib.Path(__file__).parent / 'charms' / 'machine' / 'charmcraft.yaml'
    with k.open() as f:
        ky = yaml.safe_load(f)
    with m.open() as f:
        my = yaml.safe_load(f)
    exclude = ('name', 'summary', 'description', 'containers', 'resources')
    kd = {k: v for k, v in ky.items() if k not in exclude}
    md = {k: v for k, v in my.items() if k not in exclude}
    assert kd == md
