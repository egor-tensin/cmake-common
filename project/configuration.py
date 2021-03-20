# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
from enum import Enum


class Configuration(Enum):
    '''Correspond to CMake's default CMAKE_BUILD_TYPE values.'''

    DEBUG = 'Debug'
    MINSIZEREL = 'MinSizeRel'
    RELWITHDEBINFO = 'RelWithDebInfo'
    RELEASE = 'Release'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def all():
        return tuple(Configuration)

    @staticmethod
    def parse(s):
        try:
            return Configuration(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid configuration: {s}') from e

    def variant(self):
        '''Roughly maps CMake's CMAKE_BUILD_TYPE to Boost's variant.

        AFAIK, Boost only supports debug/release, MinSizeRel and RelWithDebInfo
        are hence mapped to "release".  The libraries will still reside in
        stage/PLATFORM/CONFIGURATION/lib, if CONFIGURATION is
        MinSizeRel/RelWithDebInfo.
        '''
        if self in (Configuration.MINSIZEREL, Configuration.RELWITHDEBINFO):
            return Configuration.RELEASE.variant()
        return str(self).lower()

    def b2_variant(self):
        return [f'variant={self.variant()}']

    def b2_args(self):
        args = []
        args += self.b2_variant()
        return args

    def build_type(self):
        '''Maps to CMAKE_BUILD_TYPE.'''
        return str(self)

    def cmake_build_type(self):
        return ['-D', f'CMAKE_BUILD_TYPE={self.build_type()}']

    def cmake_args(self):
        args = []
        args += self.cmake_build_type()
        return args
