# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
from enum import Enum


class Platform(Enum):
    '''I only build for x86(-64), so here it goes.

    Win32 is just Visual Studio convention, it's effectively an alias for x86.
    '''

    X86 = 'x86'
    X64 = 'x64'
    WIN32 = 'Win32'

    def __str__(self):
        return self.value

    @staticmethod
    def all():
        return (Platform.X86, Platform.X64)

    @staticmethod
    def parse(s):
        try:
            return Platform(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f'invalid platform: {s}')

    def get_address_model(self):
        if self is Platform.X86:
            return 32
        if self is Platform.X64:
            return 64
        if self is Platform.WIN32:
            return 32
        raise NotImplementedError(f'unsupported platform: {self}')
