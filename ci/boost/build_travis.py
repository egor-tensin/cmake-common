#!/usr/bin/env python3

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This is similar to build.py, but auto-fills some parameters for build.py from
# the Travis-defined environment variables.
# Boost is built in $HOME.

import logging
import os
import sys

from build import BoostVersion, main as build_main


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _check_travis():
    if 'TRAVIS' not in os.environ:
        raise RuntimeError('not running on Travis')


def _get_build_dir():
    return _env('HOME')


def _get_boost_version():
    return _env('travis_boost_version')


def _get_configuration():
    return _env('configuration')


def _get_platform():
    return _env('platform')


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def build_travis(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)
    _check_travis()

    version = BoostVersion.from_string(_get_boost_version())
    travis_argv = [
        'download',
        '--build', _get_build_dir(),
        '--', str(version)
    ]
    build_main(travis_argv)

    travis_argv = [
        'build',
        '--configuration', _get_configuration(),
        '--platform', _get_platform(),
        '--', version.dir_path(_get_build_dir()),
    ]
    build_main(travis_argv + argv)


def main(argv=None):
    _setup_logging()
    try:
        build_travis(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
