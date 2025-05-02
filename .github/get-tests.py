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

"""Output which of the known test suites a given package has.

Assumes that the current working directory is the project root.
The package name must be provided as a commandline argument.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib


def _parse_args() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument('package')
    args = parser.parse_args()
    return args.package


def _main(project_root: pathlib.Path, package: str) -> None:
    tests = [
        test.rsplit('/')[-1]
        for test in ('unit', 'integration/pebble', 'integration/juju')
        if (project_root / package / 'tests' / test).is_dir()
    ]
    with pathlib.Path(os.environ['GITHUB_OUTPUT']).open('a') as f:
        line = f'tests={json.dumps(tests)}'
        print(line)
        print(line, file=f)


if __name__ == '__main__':
    _main(project_root=pathlib.Path(), package=_parse_args())
