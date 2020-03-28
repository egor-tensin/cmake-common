# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from collections import namedtuple
from functools import total_ordering
import os.path
import re


_Version = namedtuple('_Version', ['major', 'minor', 'patch'])


@total_ordering
class Version:
    def __init__(self, major, minor, patch):
        self._impl = _Version(major, minor, patch)

    @property
    def major(self):
        return self._impl.major

    @property
    def minor(self):
        return self._impl.minor

    @property
    def patch(self):
        return self._impl.patch

    def __lt__(self, other):
        return self._impl < other._impl

    def __eq__(self, other):
        return self._impl == other._impl

    @staticmethod
    def from_string(s):
        result = re.match(r'^(\d+)\.(\d+)\.(\d+)$', s)
        if result is None:
            raise ValueError(f'invalid Boost version: {s}')
        major = int(result.group(1))
        minor = int(result.group(2))
        patch = int(result.group(3))
        return Version(major, minor, patch)

    def __str__(self):
        return f'{self.major}.{self.minor}.{self.patch}'

    @property
    def archive_ext(self):
        return '.tar.gz'

    def dir_path(self, parent_dir):
        return os.path.join(parent_dir, self.dir_name)

    @property
    def dir_name(self):
        return f'boost_{self.major}_{self.minor}_{self.patch}'

    @property
    def archive_name(self):
        return f'{self.dir_name}{self.archive_ext}'

    def _get_bintray_url(self):
        return f'https://dl.bintray.com/boostorg/release/{self}/source/{self.archive_name}'

    def _get_sourceforge_url(self):
        return f'https://sourceforge.net/projects/boost/files/boost/{self}/{self.archive_name}/download'

    def get_download_urls(self):
        if self._impl < _Version(1, 63, 0):
            # For versions older than 1.63.0, SourceForge is the only option:
            return [self._get_sourceforge_url()]
        # Otherwise, Bintray is preferred (the official website links to it).
        return [self._get_bintray_url(), self._get_sourceforge_url()]
