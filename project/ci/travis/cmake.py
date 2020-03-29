# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Build a CMake project on Travis.

This is similar to build.py, but auto-fills some parameters for build.py from
the Travis-defined environment variables.

The project is built in $HOME/build.
'''

import argparse
import logging
import os
import os.path
import sys

from project.cmake.build import BuildParameters, build
from project.configuration import Configuration
import project.utils


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _check_travis():
    if 'TRAVIS' not in os.environ:
        raise RuntimeError('not running on Travis')


def _get_src_dir():
    return _env('TRAVIS_BUILD_DIR')


def _get_build_dir():
    return os.path.join(_env('HOME'), 'build')


def _get_configuration():
    return Configuration.parse(_env('configuration'))


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--install', metavar='DIR', dest='install_dir',
                        help='install directory')
    parser.add_argument('cmake_args', nargs='*', metavar='CMAKE_ARG', default=[],
                        help='additional CMake arguments, to be passed verbatim')
    return parser.parse_args(argv)


def build_travis(argv=None):
    args = _parse_args(argv)
    _check_travis()

    params = BuildParameters(_get_src_dir(),
                             build_dir=_get_build_dir(),
                             install_dir=args.install_dir,
                             configuration=_get_configuration(),
                             cmake_args=args.cmake_args)
    build(params)


def main(argv=None):
    with project.utils.setup_logging():
        build_travis(argv)


if __name__ == '__main__':
    main()
