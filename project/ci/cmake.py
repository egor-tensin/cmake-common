# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
import logging
import os.path
import sys

from project.ci.dirs import Dirs
from project.cmake.build import BuildParameters, build
from project.utils import setup_logging


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=Dirs.get_cmake_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--install', action='store_true',
                        help='install the project')
    parser.add_argument('--boost', metavar='DIR', dest='boost_dir',
                        help='set Boost directory path')
    parser.add_argument('--subdir', metavar='DIR',
                        help='relative project directory path')
    parser.add_argument('cmake_args', nargs='*', metavar='CMAKE_ARG', default=[],
                        help='additional CMake arguments, to be passed verbatim')
    return parser.parse_args(argv)


def build_ci(dirs, argv=None):
    args = _parse_args(argv)
    if dirs is None:
        dirs = Dirs.detect()

    src_dir = dirs.get_src_dir()
    if args.subdir:
        src_dir = os.path.join(src_dir, args.subdir)
    install_dir = dirs.get_install_dir() if args.install else None

    boost_dir = args.boost_dir
    if not boost_dir:
        # If we've built Boost using project.ci.boost already, use that.
        # Otherwise, try to use the latest pre-built Boost provided by the CI
        # system.
        boost_dir = dirs.get_boost_dir()
        if not os.path.isdir(boost_dir):
            boost_dir = dirs.get_prebuilt_boost_dir()

    params = BuildParameters(src_dir,
                             build_dir=dirs.get_cmake_dir(),
                             install_dir=install_dir,
                             platform=dirs.get_platform(),
                             configuration=dirs.get_configuration(),
                             boost_dir=boost_dir,
                             toolset=dirs.get_toolset(),
                             cmake_args=dirs.get_cmake_args() + args.cmake_args)
    build(params)


def main(argv=None):
    with setup_logging():
        build_ci(None, argv)


if __name__ == '__main__':
    main()
