# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import logging
import os.path

from project.utils import cd, run
from project.os import on_windows


class BoostDir:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise RuntimeError(f"Boost directory doesn't exist: {path}")
        self.path = path

    def _go(self):
        return cd(self.path)

    def build(self, params):
        with self._go():
            self._bootstrap_if_required()
            self._b2(params)

    def _bootstrap_if_required(self):
        if os.path.isfile(self._b2_path()):
            logging.info('Not going to bootstrap, b2 is already there')
            return
        self.bootstrap()

    def bootstrap(self):
        with self._go():
            run(self._bootstrap_path())

    def _b2(self, params):
        for b2_params in params.enum_b2_args():
            run([self._b2_path()] + b2_params)

    @staticmethod
    def _bootstrap_path():
        return os.path.join('.', BoostDir._bootstrap_name())

    @staticmethod
    def _bootstrap_name():
        ext = '.sh'
        if on_windows():
            ext = '.bat'
        return f'bootstrap{ext}'

    @staticmethod
    def _b2_path():
        return os.path.join('.', BoostDir._b2_name())

    @staticmethod
    def _b2_name():
        ext = ''
        if on_windows():
            ext = '.exe'
        return f'b2{ext}'
