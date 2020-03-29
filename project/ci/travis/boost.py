# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Download & build Boost on Travis.

This is similar to running both project.boost.download & project.boost.build,
but auto-fills some parameters from the Travis-defined environment variables.

Boost is built in $HOME/boost.
'''

import argparse
import logging
import os
import os.path
import sys

from project.boost.version import Version
from project.boost.download import DownloadParameters, download
from project.boost.build import BuildParameters, build
from project.configuration import Configuration
from project.linkage import Linkage
from project.platform import Platform
import project.utils


def _env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def _check_travis():
    if 'TRAVIS' not in os.environ:
        raise RuntimeError('not running on Travis')


def _get_build_dir():
    return _env('HOME')


def _get_boost_dir():
    return os.path.join(_get_build_dir(), 'boost')


def _get_boost_version():
    return Version.from_string(_env('travis_boost_version'))


def _get_configuration():
    return Configuration.parse(_env('configuration'))


def _get_platform():
    return Platform.parse(_env('platform'))


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--link', metavar='LINKAGE',
                        nargs='*', type=Linkage.parse,
                        help='how the libraries are linked')
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        type=Linkage.parse,
                        help='how the libraries link to the runtime')
    parser.add_argument('b2_args', metavar='B2_ARG',
                        nargs='*', default=[],
                        help='additional b2 arguments, to be passed verbatim')

    return parser.parse_args(argv)


def build_travis(argv=None):
    args = _parse_args(argv)
    _check_travis()

    version = _get_boost_version()
    build_dir = _get_build_dir()
    download(DownloadParameters(version, unpack_dir=build_dir))

    unpacked_boost_dir = version.dir_path(_get_build_dir())
    boost_dir = _get_boost_dir()
    os.rename(unpacked_boost_dir, boost_dir)

    params = BuildParameters(boost_dir,
                             platforms=(_get_platform(),),
                             configurations=(_get_configuration(),),
                             link=args.link,
                             runtime_link=args.runtime_link,
                             b2_args=args.b2_args)
    build(params)


def main(argv=None):
    with project.utils.setup_logging():
        build_travis(argv)


if __name__ == '__main__':
    main()
