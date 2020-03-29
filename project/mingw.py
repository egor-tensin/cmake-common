# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from project.os import on_windows_like


def _get_compiler_prefix(platform):
    target_arch = platform.get_address_model()
    if target_arch == 32:
        return 'i686'
    if target_arch == 64:
        return 'x86_64'
    raise RuntimeError(f'unexpected address model: {target_arch}')


def _get(platform, what):
    prefix = _get_compiler_prefix(platform)
    ext = ''
    if on_windows_like():
        # Boost.Build wants the .exe extension at the end on Cygwin.
        ext = '.exe'
    path = f'{prefix}-w64-mingw32-{what}{ext}'
    return path


def get_gcc(platform):
    return _get(platform, 'gcc')


def get_gxx(platform):
    return _get(platform, 'g++')


def get_windres(platform):
    return _get(platform, 'windres')
