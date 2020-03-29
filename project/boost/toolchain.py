# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Compiler detection.

It is assumed that Boost.Build is good enough to detect both GCC on Linux and
MSVC on Windows.  From that point on, it's just a matter of setting the correct
address-model= value.

But I also frequently use MinGW-w64, and the most convinient way to use it that
I know is making a "user config" and passing it to b2 using the --user-config
parameter.
'''

import abc
from contextlib import contextmanager
import logging

import project.os
from project.utils import temp_file


class Toolchain(abc.ABC):
    def __init__(self, platform):
        self.platform = platform

    @abc.abstractmethod
    def get_b2_args(self):
        pass

    @staticmethod
    @contextmanager
    def detect(platform, mingw=False):
        if mingw:
            with MinGW.setup(platform) as toolchain:
                yield toolchain
        else:
            yield Native(platform)

    @staticmethod
    def _format_user_config(tag, compiler, **kwargs):
        features = (f'<{k}>{v}' for k, v in kwargs.items())
        features = ' '.join(features)
        return f'using gcc : {tag} : {compiler} : {features} ;'


class Native(Toolchain):
    def get_b2_args(self):
        return [f'address-model={self.platform.get_address_model()}']


class MinGW(Toolchain):
    TAG = 'custom'

    def __init__(self, platform, config_path):
        super().__init__(platform)
        self.config_path = config_path

    def get_b2_args(self):
        return [f'--user-config={self.config_path}', f'toolset=gcc-{MinGW.TAG}']

    @staticmethod
    def _get_compiler_prefix(platform):
        target_arch = platform.get_address_model()
        if target_arch == 32:
            return 'i686'
        if target_arch == 64:
            return 'x86_64'
        raise RuntimeError(f'unexpected address model: {target_arch}')

    @staticmethod
    def _get_compiler_path(platform):
        prefix = MinGW._get_compiler_prefix(platform)
        ext = ''
        if project.os.on_windows_like():
            # Boost.Build wants the .exe extension at the end on Cygwin.
            ext = '.exe'
        path = f'{prefix}-w64-mingw32-g++{ext}'
        return path

    @staticmethod
    def _format_mingw_user_config(platform):
        compiler = MinGW._get_compiler_path(platform)
        features = {
            'target-os': 'windows',
            'address-model': platform.get_address_model(),
        }
        return Toolchain._format_user_config(MinGW.TAG, compiler, **features)

    @staticmethod
    @contextmanager
    def setup(platform):
        config = MinGW._format_mingw_user_config(platform)
        logging.info('Using user config:\n%s', config)
        tmp = temp_file(config, mode='w', prefix='mingw_w64_', suffix='.jam')
        with tmp as path:
            yield MinGW(platform, path)
