# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
from enum import Enum


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

    def b2_args(self, name='link'):
        return [f'{name}={self}']
