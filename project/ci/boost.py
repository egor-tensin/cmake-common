# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
import logging
import os
import os.path
import sys

from project.boost.download import DownloadParameters, download
from project.boost.build import BuildParameters, build
from project.linkage import Linkage


def _parse_args(dirs, argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=dirs.get_boost_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--link', metavar='LINKAGE',
                        nargs='*', type=Linkage.parse,
                        help='how the libraries are linked')
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        type=Linkage.parse,
                        help='how the libraries link to the runtime')
    parser.add_argument('--mingw', action='store_true',
                        help='build using MinGW-w64')
    parser.add_argument('b2_args', metavar='B2_ARG',
                        nargs='*', default=[],
                        help='additional b2 arguments, to be passed verbatim')

    return parser.parse_args(argv)


def build_ci(dirs, argv=None):
    args = _parse_args(dirs, argv)

    version = dirs.get_boost_version()
    build_dir = dirs.get_build_dir()
    download(DownloadParameters(version, unpack_dir=build_dir))

    unpacked_boost_dir = version.dir_path(build_dir)
    boost_dir = dirs.get_boost_dir()
    os.rename(unpacked_boost_dir, boost_dir)

    params = BuildParameters(boost_dir,
                             platforms=(dirs.get_platform(),),
                             configurations=(dirs.get_configuration(),),
                             link=args.link,
                             runtime_link=args.runtime_link,
                             mingw=args.mingw,
                             b2_args=args.b2_args)
    build(params)