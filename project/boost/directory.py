# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import logging
import os.path

from project.boost.toolchain import BootstrapToolchain
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
            self._bootstrap_if_required(params)
            self._b2(params)

    def _bootstrap_if_required(self, params):
        if os.path.isfile(self._b2_path()):
            logging.info('Not going to bootstrap, b2 is already there')
            return
        self.bootstrap(params)

    def bootstrap(self, params):
        with self._go():
            toolchain = BootstrapToolchain.detect(params.toolset)
            run([self._bootstrap_path()] + self._bootstrap_args(toolchain))

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
    def _bootstrap_args(toolchain):
        if on_windows():
            return toolchain.get_bootstrap_bat_args()
        return toolchain.get_bootstrap_sh_args()

    @staticmethod
    def _b2_path():
        return os.path.join('.', BoostDir._b2_name())

    @staticmethod
    def _b2_name():
        ext = ''
        if on_windows():
            ext = '.exe'
        return f'b2{ext}'
