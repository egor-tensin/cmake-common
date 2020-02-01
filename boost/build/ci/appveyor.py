#!/usr/bin/env python3

# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''Download & build Boost on AppVeyor.

This is similar to build.py, but auto-fills some parameters for build.py from
the AppVeyor-defined environment variables.  This script is rarely usefull,
since AppVeyor images come with lots of pre-built Boost distributions, but
still.

Boost is built in C:\projects\boost.
'''

import argparse
import logging
import os
import os.path
import sys


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _check_appveyor():
    if 'APPVEYOR' not in os.environ:
        raise RuntimeError('not running on AppVeyor')


def _get_build_dir():
    return 'C:\\projects'


def _get_boost_dir():
    return os.path.join(_get_build_dir(), 'boost')


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

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--link', metavar='LINKAGE', nargs='*',
                        help='how the libraries are linked (i.e. static/shared)')
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        help='how the libraries link to the runtime')
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
    appveyor_argv = [
        'download',
        '--unpack', _get_build_dir(),
        '--', str(version)
    ]
    build_main(appveyor_argv)

    unpacked_boost_dir = version.dir_path(_get_build_dir())
    boost_dir = _get_boost_dir()
    os.rename(unpacked_boost_dir, boost_dir)

    appveyor_argv = [
        'build',
        '--configuration', _get_configuration(),
        '--platform', _get_platform(),
    ]
    if args.link is not None:
        appveyor_argv.append('--link')
        appveyor_argv += args.link
    if args.runtime_link is not None:
        appveyor_argv += ['--runtime-link', args.runtime_link]
    appveyor_argv += ['--', boost_dir]
    build_main(appveyor_argv + args.b2_args)


def main(argv=None):
    _setup_logging()
    try:
        build_appveyor(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
