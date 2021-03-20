# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
from enum import Enum
import platform
import os.path

from project.os import on_windows


class Platform(Enum):
    # I only build for x86(-64), so here it goes.
    X86 = 'x86'
    X64 = 'x64'
    # 'auto' means that no additional arguments will be passed to either
    # Boost's b2 nor CMake (except on Windows, see below).
    AUTO = 'auto'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def windows_native():
        # On Windows, no explicit platform would mean x64 for VS 2019 and x86
        # for VS 2017.  To account for this discrepancy, it is assumed that
        # Windows builds can only target either x86 or x64 (which I don't think
        # is true?), and we default to x64 most of the time.
        #
        # Source: https://stackoverflow.com/a/12578715/514684
        if platform.machine().endswith('64'):
            return Platform.X64
        return Platform.X86

    @staticmethod
    def all():
        return Platform.X86, Platform.X64,

    @staticmethod
    def parse(s):
        try:
            if s == 'Win32':
                # Visual Studio/AppVeyor convention:
                return Platform.X86
            return Platform(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid platform: {s}') from e

    def mingw_prefix(self):
        if self is Platform.AUTO:
            if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().mingw_prefix()
            # On Linux, assume that the target is x64.
            return Platform.X64.mingw_prefix()
        if self is Platform.X86:
            return 'i686'
        if self is Platform.X64:
            return 'x86_64'
        raise NotImplementedError(f'unsupported platform: {self}')

    def address_model(self):
        '''Maps to Boost's address-model.'''
        if self is Platform.AUTO:
            if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().address_model()
            # On Linux, assume that the target is x64.
            raise RuntimeError('cannot determine address model unless the target platform is specified explicitly')
        if self is Platform.X86:
            return 32
        if self is Platform.X64:
            return 64
        raise NotImplementedError(f'unsupported platform: {self}')

    def stagedir(self, configuration):
        '''Path to the built libraries inside the Boost build directory.'''
        if self is Platform.AUTO:
            if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().stagedir(configuration)
            # On Linux, the libraries are stored in stage/auto/CONFIGURATION/lib.
        return os.path.join('stage', str(self), str(configuration))

    def boost_librarydir(self, configuration):
        '''Same as above, but for CMake; adds /lib/ at the end.'''
        return os.path.join(self.stagedir(configuration), 'lib')

    def b2_address_model(self):
        if self is Platform.AUTO and not on_windows():
            # On Linux, don't specify the architecture explicitly (it is
            # assumed that the host architecture will be targeted).
            return []
        return [f'address-model={self.address_model()}']

    def b2_stagedir(self, configuration):
        return [f'--stagedir={self.stagedir(configuration)}']

    def b2_args(self, configuration):
        args = []
        args += self.b2_address_model()
        args += self.b2_stagedir(configuration)
        return args

    def makefile_toolchain_file(self):
        # For Makefile generators, we make a special toolchain file that
        # specifies the -m32/-m64 flags, etc.
        if self is Platform.AUTO:
            # Let the compiler decide.
            return ''
        if self is Platform.X86:
            address_model = 32
        elif self is Platform.X64:
            address_model = 64
        else:
            raise NotImplementedError(f'unsupported platform: {self}')
        return f'''
set(CMAKE_C_FLAGS   -m{address_model})
set(CMAKE_CXX_FLAGS -m{address_model})
'''

    def msvc_arch(self):
        '''Maps to CMake's -A argument for MSVC.'''
        if self is Platform.AUTO:
            if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().msvc_arch()
            # I don't think the -A argument is supported on any generators
            # except the Visual Studio ones.
            raise RuntimeError('-A parameter is only supported for Visual Studio generators')
        if self is Platform.X86:
            return 'Win32'
        if self is Platform.X64:
            return 'x64'
        raise NotImplementedError(f'unsupported platform: {self}')
