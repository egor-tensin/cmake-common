#!/usr/bin/env python3

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

Picking the target platform is build system-specific.  On Visual Studio, pass
the target platform using the `-A` flag like this:

    > python -m project.cmake.build --install path\to\somewhere -- examples\simple -A Win32
    ...

Using GCC-like compilers, the best way is to use CMake toolchain files (see
toolchains/cmake in this repository for examples).

    $ python -m project.cmake.build --install path/to/somewhere -- examples/simple -D CMAKE_TOOLCHAIN_FILE="$( pwd )/toolchains/mingw-x86.cmake"
    ...
'''

import argparse
from contextlib import contextmanager
import logging
import os
import os.path
import sys
import tempfile

from project.configuration import Configuration
import project.utils


def run_cmake(cmake_args):
    return project.utils.run(['cmake'] + cmake_args)


class GenerationPhase:
    def __init__(self, build_dir, params):
        self.build_dir = build_dir
        self.params = params

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.params)

    @staticmethod
    def _to_cmake_args(build_dir, params):
        result = []
        if params.install_dir is not None:
            result += ['-D', f'CMAKE_INSTALL_PREFIX={params.install_dir}']
        if params.configuration is not None:
            result += ['-D', f'CMAKE_BUILD_TYPE={params.configuration}']
        if params.cmake_args is not None:
            result += params.cmake_args
        result += [f'-B{build_dir}', f'-H{params.src_dir}']
        return result

    def run(self):
        run_cmake(self._cmake_args())


class BuildPhase:
    def __init__(self, build_dir, params):
        self.build_dir = build_dir
        self.params = params

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.params)

    @staticmethod
    def _to_cmake_args(build_dir, params):
        result = ['--build', build_dir]
        if params.configuration is not None:
            result += ['--config', str(params.configuration)]
        if params.install_dir is not None:
            result += ['--target', 'install']
        return result

    def run(self):
        run_cmake(self._cmake_args())


class BuildParameters:
    def __init__(self, src_dir, build_dir=None, install_dir=None,
                 configuration=Configuration.DEBUG, cmake_args=None):

        src_dir = project.utils.normalize_path(src_dir)
        if build_dir is not None:
            build_dir = project.utils.normalize_path(build_dir)
        if install_dir is not None:
            install_dir = project.utils.normalize_path(install_dir)
        if cmake_args is None:
            cmake_args = []

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.install_dir = install_dir
        self.configuration = configuration
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
        gen_phase = GenerationPhase(build_dir, params)
        gen_phase.run()
        build_phase = BuildPhase(build_dir, params)
        build_phase.run()


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--build', metavar='DIR', dest='build_dir',
                        type=project.utils.normalize_path,
                        help='build directory (temporary directory unless specified)')
    parser.add_argument('--install', metavar='DIR', dest='install_dir',
                        type=project.utils.normalize_path,
                        help='install directory')

    configuration_options = '/'.join(map(str, Configuration.all()))
    parser.add_argument('--configuration', metavar='CONFIG',
                        type=Configuration.parse, default=Configuration.DEBUG,
                        help=f'build configuration ({configuration_options})')

    parser.add_argument('src_dir', metavar='DIR',
                        type=project.utils.normalize_path,
                        help='source directory')
    parser.add_argument('cmake_args', metavar='CMAKE_ARG',
                        nargs='*', default=[],
                        help='additional CMake arguments, to be passed verbatim')

    return parser.parse_args(argv)


def main(argv=None):
    with project.utils.setup_logging():
        build(BuildParameters.from_args(_parse_args(argv)))


if __name__ == '__main__':
    main()
