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
import tempfile

import project.os


class Toolchain(abc.ABC):
    def __init__(self, platform):
        self.platform = platform

    @abc.abstractmethod
    def get_b2_args(self):
        pass


class NativeToolchain(Toolchain):
    def get_b2_args(self):
        return [f'address-model={self.platform.get_address_model()}']


class MingwToolchain(Toolchain):
    TAG = 'custom'

    def __init__(self, platform, config_path):
        super().__init__(platform)
        self.config_path = config_path

    def get_b2_args(self):
        return [f'--user-config={self.config_path}', f'toolset=gcc-{MingwToolchain.TAG}']


def _native_toolchain(platform):
    return NativeToolchain(platform)


def _get_mingw_prefix(platform):
    target_arch = platform.get_address_model()
    if target_arch == 32:
        return 'i686'
    if target_arch == 64:
        return 'x86_64'
    raise RuntimeError(f'unexpected address model: {target_arch}')


def _get_mingw_path(platform):
    prefix = _get_mingw_prefix(platform)
    ext = ''
    if project.os.on_windows_like():
        # Boost.Build wants the .exe extension at the end on Cygwin.
        ext = '.exe'
    path = f'{prefix}-w64-mingw32-g++{ext}'
    return path


def _format_user_config(tag, compiler, **kwargs):
    features = (f'<{k}>{v}' for k, v in kwargs.items())
    features = ' '.join(features)
    return f'using gcc : {tag} : {compiler} : {features} ;'


def _format_mingw_user_config(platform):
    compiler = _get_mingw_path(platform)
    features = {
        'target-os': 'windows',
        'address-model': platform.get_address_model(),
    }
    return _format_user_config(MingwToolchain.TAG, compiler, **features)


@contextmanager
def _mingw_toolchain(platform):
    tmp = tempfile.NamedTemporaryFile(mode='w', prefix='mingw_w64_', suffix='.jam')
    with tmp as file:
        config = _format_mingw_user_config(platform)
        logging.info('Using user config:\n%s', config)
        file.write(config)
        file.flush()
        try:
            yield MingwToolchain(platform, file.name)
        finally:
            logging.info('Removing temporary user config file')


@contextmanager
def detect_toolchain(platform, mingw=False):
    if mingw:
        with _mingw_toolchain(platform) as toolchain:
            yield toolchain
    else:
        yield _native_toolchain(platform)
