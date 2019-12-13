#!/usr/bin/env python3

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This is similar to build.py, but auto-fills some parameters for build.py from
# the AppVeyor-defined environment variables.
# The project is built in C:\Projects\build.

from enum import Enum
import logging
import os
import sys

from build import build


class Image(Enum):
    VS_2013 = 'Visual Studio 2013'
    VS_2015 = 'Visual Studio 2015'
    VS_2017 = 'Visual Studio 2017'
    VS_2019 = 'Visual Studio 2019'

    def __str__(self):
        return self.value


def _parse_image(s):
    try:
        return Image(s)
    except ValueError as e:
        raise ValueError(f'unsupported AppVeyor image: {s}') from e


class Generator(Enum):
    VS_2013 = 'Visual Studio 12 2013'
    VS_2015 = 'Visual Studio 14 2015'
    VS_2017 = 'Visual Studio 15 2017'
    VS_2019 = 'Visual Studio 16 2019'

    def __str__(self):
        return self.value

    @staticmethod
    def from_image(image):
        if image is Image.VS_2013:
            return Generator.VS_2013
        if image is Image.VS_2015:
            return Generator.VS_2015
        if image is Image.VS_2017:
            return Generator.VS_2017
        if image is Image.VS_2019:
            return Generator.VS_2019
        raise RuntimeError(f"don't know which generator to use for image: {image}")


class Platform(Enum):
    x86 = 'Win32'
    X64 = 'x64'

    def __str__(self):
        return self.value


def _parse_platform(s):
    try:
        return Platform(s)
    except ValueError as e:
        raise ValueError(f'unsupported AppVeyor platform: {s}') from e


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _get_src_dir():
    return _env('APPVEYOR_BUILD_FOLDER')


def _get_build_dir():
    return R'C:\Projects\build'


def _get_generator():
    image = _parse_image(_env('APPVEYOR_BUILD_WORKER_IMAGE'))
    return str(Generator.from_image(image))


def _get_platform():
    return str(_parse_platform(_env('PLATFORM')))


def _get_configuration():
    return _env('CONFIGURATION')


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def build_appveyor(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)
    appveyor_argv = [
        '--src', _get_src_dir(),
        '--build', _get_build_dir(),
        '--generator', _get_generator(),
        '--platform', _get_platform(),
        '--configuration', _get_configuration(),
    ]
    build(appveyor_argv + argv)


def main(argv=None):
    _setup_logging()
    try:
        build_appveyor(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
