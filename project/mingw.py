# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.


class MinGW:
    def __init__(self, platform):
        self.prefix = platform.mingw_prefix()

    def _get(self, what):
        return f'{self.prefix}-w64-mingw32-{what}'

    def gcc(self):
        return self._get('gcc')

    def gxx(self):
        return self._get('g++')

    def ar(self):
        return self._get('gcc-ar')

    def ranlib(self):
        return self._get('gcc-ranlib')

    def windres(self):
        return self._get('windres')
