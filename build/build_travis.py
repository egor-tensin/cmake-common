#!/usr/bin/env python3

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This is similar to build.py, but auto-fills some parameters for build.py from
# the Travis-defined environment variables.
# The project is built in $HOME/build.

import logging
import os
import os.path
import sys

from build import build


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _get_src_dir():
    return _env('TRAVIS_BUILD_DIR')


def _get_build_dir():
    return os.path.join(_env('HOME'), 'build')


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def build_travis(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)
    travis_argv = [
        '--src', _get_src_dir(),
        '--build', _get_build_dir(),
    ]
    build(travis_argv + argv)


def main(argv=None):
    _setup_logging()
    try:
        build_travis(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
