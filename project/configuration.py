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
        return self.value

    @staticmethod
    def all():
        return tuple(Configuration)

    @staticmethod
    def parse(s):
        try:
            return Configuration(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f'invalid configuration: {s}')

    def to_boost_variant(self):
        '''Roughly maps CMake's CMAKE_BUILD_TYPE to Boost's variant.

        AFAIK, Boost only supports debug/release, MinSizeRel and RelWithDebInfo
        are hence mapped to "release".  The libraries will still reside in
        stage/PLATFORM/CONFIGURATION/lib, if CONFIGURATION is
        MinSizeRel/RelWithDebInfo.
        '''
        if self in (Configuration.MINSIZEREL, Configuration.RELWITHDEBINFO):
            return Configuration.RELEASE.to_boost_variant()
        return str(self).lower()
