#!/usr/bin/env python3

# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This is similar to build.py, but auto-fills some parameters for build.py from
# the AppVeyor-defined environment variables.
# This script is rarely usefull, since AppVeyor images come with lots of
# pre-built Boost distributions, but still.
# Boost is built in C:\.

import argparse
import logging
import os
import sys


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _check_appveyor():
    if 'APPVEYOR' not in os.environ:
        raise RuntimeError('not running on AppVeyor')


def _get_build_dir():
    return 'C:\\'


def _get_boost_version():
    return _env('appveyor_boost_version')


def _get_configuration():
    return _env('CONFIGURATION')


def _get_platform():
    return _env('PLATFORM')


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser()
    parser.add_argument('b2_args', nargs='*', metavar='B2_ARG', default=[],
                        help='additional b2 arguments, to be passed verbatim')
    return parser.parse_args(argv)


def build_appveyor(argv=None):
    args = _parse_args(argv)
    _check_appveyor()

    this_module_dir = os.path.dirname(os.path.abspath(__file__))
    parent_module_dir = os.path.dirname(this_module_dir)
    sys.path.insert(1, parent_module_dir)
    from build import BoostVersion, main as build_main

    version = BoostVersion.from_string(_get_boost_version())
    travis_argv = [
        'download',
        '--unpack', _get_build_dir(),
        '--', str(version)
    ]
    build_main(travis_argv)

    travis_argv = [
        'build',
        '--configuration', _get_configuration(),
        '--platform', _get_platform(),
        '--', version.dir_path(_get_build_dir()),
    ]
    build_main(travis_argv + args.b2_args)


def main(argv=None):
    _setup_logging()
    try:
        build_appveyor(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
