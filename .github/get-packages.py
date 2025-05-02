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

"""Output changed packages, or all packages if global config files have changed.

Assumes that the current working directory is the project root.
The git reference to diff with must be provided as a commandline argument.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import string
import subprocess

_ALPHABET = tuple(string.ascii_lowercase)
_GLOBAL_FILES = ('pyproject.toml', 'justfile', '.github')


def _parse_args() -> str | None:
    parser = argparse.ArgumentParser()
    parser.add_argument('git_base_ref', default=None)
    args = parser.parse_args()
    return args.git_base_ref


def _main(project_root: pathlib.Path, git_base_ref: str | None) -> None:
    packages = _get_changed_packages(project_root=project_root, git_base_ref=git_base_ref)
    _set_output(packages)


def _get_changed_packages(project_root: pathlib.Path, git_base_ref: str | None) -> list[str]:
    all_packages = sorted([
        '_charmlibs',
        *(
            path.name
            for path in project_root.iterdir()
            if path.is_dir() and path.name.startswith(_ALPHABET)
        ),
    ])
    if not git_base_ref:
        print('Using all packages because no git base ref was provided.')
        return all_packages
    git_diff_cmd = ['git', 'diff', '--name-only', f'origin/{git_base_ref}']
    git_diff = subprocess.run(git_diff_cmd, capture_output=True, text=True, cwd=project_root)
    changes = git_diff.stdout.split('\n')
    names = {change.split('/')[0] for change in changes}
    # record which packages have changed, or all if global config files have changed
    global_changes = sorted(name for name in names if name in _GLOBAL_FILES)
    if global_changes:
        print(f'Using all packages because global files were changed: {global_changes}')
        return all_packages
    print(f'Using packages that are changed compared to {git_base_ref}.')
    return [p for p in all_packages if p in names]


def _set_output(packages: list[str]) -> None:
    with pathlib.Path(os.environ['GITHUB_OUTPUT']).open('a') as f:
        line = f'packages={json.dumps(packages)}'
        print(line)
        print(line, file=f)


if __name__ == '__main__':
    _main(project_root=pathlib.Path(), git_base_ref=_parse_args())
