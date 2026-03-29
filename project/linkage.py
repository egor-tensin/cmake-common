# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
from enum import Enum
import logging

from project.os import on_linux_like


class Linkage(Enum):
    STATIC = 'static'
    SHARED = 'shared'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def all():
        return tuple(Linkage)

    @staticmethod
    def parse(s):
        try:
            return Linkage(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid linkage: {s}') from e

    # For my development, I link everything statically (to be able to pull the
    # binaries from a CI, etc. and run them everywhere):
    @staticmethod
    def default_link():
        return Linkage.STATIC

    @staticmethod
    def default_runtime_link():
        return Linkage.STATIC

    @staticmethod
    def validate_linkage(link, runtime_link):
        if runtime_link is Linkage.STATIC:
            if link is Linkage.SHARED:
                logging.warning("Cannot link the runtime statically to a dynamic library, going to link dynamically")
                runtime_link = Linkage.SHARED
            elif on_linux_like():
                logging.warning("Cannot link to the GNU C Library or BSD libc (which are assumed) statically, going to link dynamically")
                runtime_link = Linkage.SHARED
        return link, runtime_link

    def b2_args_link(self):
        return [f'link={self}']

    def b2_args_runtime_link(self):
        return [f'runtime-link={self}']

    def cmake_args_link(self):
        if self is Linkage.STATIC:
            return ['-DBoost_USE_STATIC_LIBS=ON']
        return []

    def cmake_args_runtime_link(self):
        if self is Linkage.STATIC:
            return [
                '-DBoost_USE_STATIC_RUNTIME=ON',
                '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded$<$<CONFIG:Debug>:Debug>',
            ]
        return []
