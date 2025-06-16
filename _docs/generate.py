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

"""Generate reference/non-relation-libs-table.rst from reference/non-relation-libs-raw.csv."""

from __future__ import annotations

import csv
import pathlib
import typing

_EMOJIS = {
    # statuses
    'recommended': '✅',
    'dep': '↪️',
    'legacy': '🪦',
    'team': '🚫',
    # kinds
    # 'PyPI': '🐍',
    # 'git': '🔧',
    # 'Charmhub': '✨',
    # substrates
    'machine': '🖥️',
    'K8s': '☸️',
    # other
    # 'docs': '📚',
    # 'src': '⌨️',
}
_STATUS_TOOLTIPS = {
    'recommended': 'Recommended for use in new charms today!',
    'dep': 'Dependency of other libs, unlikely to be needed directly.',
    'legacy': 'There are better alternatives available.',
    'team': 'Team internal lib, may not be stable for external use.',
}
_KIND_SORTKEYS = {'PyPI': 0, 'git': 1, 'Charmhub': 2, '': 3}
_STATUS_SORTKEYS = {s: i for i, s in enumerate(('recommended', 'dep', '', 'legacy', 'team'))}
_TABLE_HEADER_TEMPLATE = """..
    This file was automatically generated.
    It should not be manually edited!
    Instead, edit {csv_file} and then run {script_file}

.. list-table::
   :class: sphinx-datatable
   :widths: 1, 40, 1, 60
   :header-rows: 1

   * -
     - name
     - kind
     - description
"""


class _CSVRow(typing.TypedDict, total=True):
    name: str
    status: str
    url: str
    docs: str
    src: str
    kind: str
    machine: str
    K8s: str
    description: str


def _generate_non_relation_libs_table():
    raw = pathlib.Path('reference/non-relation-libs-raw.csv')
    with raw.open() as f:
        entries: list[_CSVRow] = list(csv.DictReader(f))  # type: ignore
    chunks = [_TABLE_HEADER_TEMPLATE.format(csv_file=raw, script_file=pathlib.Path(__file__).name)]
    rows = [(_status(entry), _name(entry), _kind(entry), _description(entry)) for entry in entries]
    for row in sorted(rows, key=lambda r: (r[0], r[2], r[3], r[1])):  # sort: status, kind, desc
        first, *rest = (f' {cell}' if cell and not cell.startswith('\n') else cell for cell in row)
        chunks.append(f'   * -{first}\n')
        chunks.extend(f'     -{line}\n' for line in rest)
    pathlib.Path('reference/non-relation-libs-table.rst').write_text(''.join(chunks))


def _status(entry: _CSVRow) -> str:
    status = entry['status']
    prefix = _hidden_text(_STATUS_SORTKEYS[status])
    if status not in _EMOJIS:
        return prefix
    if status not in _STATUS_TOOLTIPS:
        return f'{prefix}       | {_EMOJIS[status]}'
    return (
        prefix.rstrip()
        + '\n          '
        + f'<div class="emoji-div">{_EMOJIS[status]}'
        + f'<div class="emoji-tooltip">{_STATUS_TOOLTIPS[status]}</div>'
        + '</div>'
        + '\n\n'
    )


def _name(entry: _CSVRow) -> str:
    main_link = _rst_link(entry['name'], entry['url'])
    extra_links = ', '.join([
        _rst_link(_EMOJIS.get(text, '') + text, url)
        for text in ('docs', 'src')
        if (url := entry[text])
    ])
    if not extra_links:
        return main_link
    return f'{main_link} ({extra_links})'


def _kind(entry: _CSVRow) -> str:
    kind = entry['kind']
    prefix = _hidden_text(_KIND_SORTKEYS[kind])
    kind_str = _EMOJIS.get(kind, '') + kind
    if not kind_str:
        return prefix
    return f'{prefix}       | {kind_str}'


def _description(entry: _CSVRow) -> str:
    substrates = ('machine', 'K8s')
    sortkeys = [
        *(0 if entry[s] else 1 for s in substrates),
        _STATUS_SORTKEYS[entry['status']],
        _KIND_SORTKEYS[entry['kind']],
        entry['name'],
    ]
    prefix = _hidden_text(''.join(str(k) for k in sortkeys))
    descriptions: list[str] = []
    if subs := [_EMOJIS.get(s, '') + s for s in substrates if entry[s]]:
        descriptions.append(' '.join(subs))
    if desc := entry['description']:
        descriptions.append(desc)
    if not descriptions:
        return prefix
    description = '\n'.join(descriptions).replace('\n', '\n       | ')
    return f'{prefix}       | {description}'


def _rst_link(name: str, url: str) -> str:
    return f'`{name} <{url}>`__'


def _hidden_text(msg: object) -> str:
    return f"""
       .. raw:: html

          <span style="display:none;">{msg}</span>

"""


if __name__ == '__main__':
    _generate_non_relation_libs_table()
