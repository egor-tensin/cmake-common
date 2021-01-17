# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''Supported platform/build system/compiler combinations include, but are not
limited to:

* Linux / make / Clang,
* Linux / make / GCC,
* Linux / make / MinGW-w64,
* Windows / make / Clang (clang.exe & clang++.exe),
* Windows / make / Clang (clang-cl.exe, Boost 1.69.0 or higher only),
* Windows / make / MinGW-w64,
* Windows / msbuild / MSVC,
* Cygwin / make / Clang,
* Cygwin / make / GCC,
* Cygwin / make / MinGW-w64.
'''

import argparse
from enum import Enum


class ToolchainType(Enum):
    AUTO = 'auto'   # This most commonly means GCC on Linux and MSVC on Windows.
    MSVC = 'msvc'   # Force MSVC.
    GCC = 'gcc'     # Force GCC.
    MINGW = 'mingw' # As in MinGW-w64; GCC with the PLATFORM-w64-mingw32 prefix.
    CLANG = 'clang'
    CLANG_CL = 'clang-cl'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def all():
        return tuple(ToolchainType)

    @staticmethod
    def parse(s):
        try:
            return ToolchainType(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid toolset: {s}') from e
