# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
from enum import Enum
import platform


class Platform(Enum):
    '''I only build for x86(-64), so here it goes.'''

    X86 = 'x86'
    X64 = 'x64'

    def __str__(self):
        return self.value

    @staticmethod
    def native():
        # Source: https://stackoverflow.com/a/12578715/514684
        if platform.machine().endswith('64'):
            return Platform.X64
        return Platform.X86

    @staticmethod
    def all():
        return tuple(Platform)

    @staticmethod
    def parse(s):
        try:
            if s == 'Win32':
                # AppVeyor convention:
                return Platform.X86
            return Platform(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f'invalid platform: {s}')

    def get_address_model(self):
        '''Maps to Boost's address-model.'''
        if self is Platform.X86:
            return 32
        if self is Platform.X64:
            return 64
        raise NotImplementedError(f'unsupported platform: {self}')

    def get_cmake_arch(self):
        '''Maps to CMake's -A argument for MSVC.'''
        if self is Platform.X86:
            return 'Win32'
        if self is Platform.X64:
            return 'x64'
        raise NotImplementedError(f'unsupported platform: {self}')
