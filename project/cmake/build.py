# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Build a CMake project.

This script is used basically to invoke the CMake executable in a
cross-platform way (provided the platform has Python 3, of course).  The
motivation was to merge my Travis and AppVeyor build scripts (largely similar,
but written in bash and PowerShell, respectively).

A simple usage example:

    $ python -m project.cmake.build --configuration Release --install path/to/somewhere -- examples/simple
    ...

    $ ./path/to/somewhere/bin/foo
    foo
'''

import argparse
from contextlib import contextmanager
import logging
import os
import os.path
import sys
import tempfile

from project.cmake.toolchain import Toolchain
from project.configuration import Configuration
from project.platform import Platform
from project.utils import normalize_path, run, setup_logging


DEFAULT_CONFIGURATION = Configuration.DEBUG


def run_cmake(cmake_args):
    return run(['cmake'] + cmake_args)


class GenerationPhase:
    def __init__(self, src_dir, build_dir, install_dir=None,
                 platform=None, configuration=DEFAULT_CONFIGURATION,
                 boost_dir=None, mingw=False, cmake_args=None):
        src_dir = normalize_path(src_dir)
        build_dir = normalize_path(build_dir)
        if install_dir is not None:
            install_dir = normalize_path(install_dir)
        if boost_dir is not None:
            boost_dir = normalize_path(boost_dir)
        cmake_args = cmake_args or []

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.install_dir = install_dir
        self.platform = platform
        self.configuration = configuration
        self.boost_dir = boost_dir
        self.mingw = mingw
        self.cmake_args = cmake_args

    def _cmake_args(self, toolchain):
        result = []
        if self.install_dir is not None:
            result += ['-D', f'CMAKE_INSTALL_PREFIX={self.install_dir}']
        result += toolchain.get_cmake_args()
        result += ['-D', f'CMAKE_BUILD_TYPE={self.configuration}']
        result += self._get_boost_args()
        result += self.cmake_args
        result += [f'-B{self.build_dir}', f'-H{self.src_dir}']
        return result

    def _get_boost_args(self):
        if self.boost_dir is None:
            return []
        stagedir = self._stagedir(self.boost_dir, self.platform, self.configuration)
        return [
            '-D', f'BOOST_ROOT={self.boost_dir}',
            '-D', f'BOOST_LIBRARYDIR={stagedir}',
        ]

    @staticmethod
    def _stagedir(boost_dir, platform, configuration):
        if platform is None:
            platform = Platform.native()
        return os.path.join(boost_dir, 'stage', str(platform), str(configuration), 'lib')

    def run(self):
        with Toolchain.detect(self.platform, self.build_dir, mingw=self.mingw) as toolchain:
            run_cmake(self._cmake_args(toolchain))


class BuildPhase:
    def __init__(self, build_dir, install_dir=None,
                 configuration=DEFAULT_CONFIGURATION):

        build_dir = normalize_path(build_dir)

        self.build_dir = build_dir
        self.install_dir = install_dir
        self.configuration = configuration

    def _cmake_args(self):
        result = ['--build', self.build_dir]
        result += ['--config', str(self.configuration)]
        if self.install_dir is not None:
            result += ['--target', 'install']
        return result

    def run(self):
        run_cmake(self._cmake_args())


class BuildParameters:
    def __init__(self, src_dir, build_dir=None, install_dir=None,
                 platform=None, configuration=DEFAULT_CONFIGURATION,
                 boost_dir=None, mingw=False, cmake_args=None):

        src_dir = normalize_path(src_dir)
        if build_dir is not None:
            build_dir = normalize_path(build_dir)
        if install_dir is not None:
            install_dir = normalize_path(install_dir)
        if boost_dir is not None:
            boost_dir = normalize_path(boost_dir)
        cmake_args = cmake_args or []

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.install_dir = install_dir
        self.platform = platform
        self.configuration = configuration
        self.boost_dir = boost_dir
        self.mingw = mingw
        self.cmake_args = cmake_args

    @staticmethod
    def from_args(args):
        return BuildParameters(**vars(args))

    @contextmanager
    def create_build_dir(self):
        if self.build_dir is not None:
            logging.info('Build directory: %s', self.build_dir)
            yield self.build_dir
            return

        with tempfile.TemporaryDirectory(dir=os.path.dirname(self.src_dir)) as build_dir:
            logging.info('Build directory: %s', build_dir)
            try:
                yield build_dir
            finally:
                logging.info('Removing build directory: %s', build_dir)
            return


def build(params):
    with params.create_build_dir() as build_dir:
        gen_phase = GenerationPhase(params.src_dir, build_dir,
                                    install_dir=params.install_dir,
                                    platform=params.platform,
                                    configuration=params.configuration,
                                    boost_dir=params.boost_dir,
                                    mingw=params.mingw,
                                    cmake_args=params.cmake_args)
        gen_phase.run()
        build_phase = BuildPhase(build_dir, install_dir=params.install_dir,
                                 configuration=params.configuration)
        build_phase.run()


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--build', metavar='DIR', dest='build_dir',
                        type=normalize_path,
                        help='build directory (temporary directory unless specified)')
    parser.add_argument('--install', metavar='DIR', dest='install_dir',
                        type=normalize_path,
                        help='install directory')

    platform_options = '/'.join(map(str, Platform.all()))
    configuration_options = '/'.join(map(str, Configuration.all()))

    parser.add_argument('--platform', metavar='PLATFORM',
                        type=Platform.parse,
                        help=f'target platform ({platform_options})')
    parser.add_argument('--configuration', metavar='CONFIG',
                        type=Configuration.parse, default=DEFAULT_CONFIGURATION,
                        help=f'build configuration ({configuration_options})')

    parser.add_argument('--boost', metavar='DIR', dest='boost_dir',
                        type=normalize_path,
                        help='set Boost directory path')

    parser.add_argument('--mingw', action='store_true',
                        help='build using MinGW-w64')

    parser.add_argument('src_dir', metavar='DIR',
                        type=normalize_path,
                        help='source directory')
    parser.add_argument('cmake_args', metavar='CMAKE_ARG',
                        nargs='*', default=[],
                        help='additional CMake arguments, to be passed verbatim')

    return parser.parse_args(argv)


def main(argv=None):
    with setup_logging():
        build(BuildParameters.from_args(_parse_args(argv)))


if __name__ == '__main__':
    main()
