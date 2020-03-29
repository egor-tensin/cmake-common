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

    $ %(prog)s --configuration Release --install path/to/somewhere -- ../examples/simple
    ...

    $ ./path/to/somewhere/bin/foo
    foo

Picking the target platform is build system-specific.  On Visual Studio, pass
the target platform using the `-A` flag like this:

    > %(prog)s --install path\to\somewhere -- ..\examples\simple -A Win32
    ...

Using GCC-like compilers, the best way is to use CMake toolchain files (see
cmake/toolchains in this repository for examples).

    $ %(prog)s --install path/to/somewhere -- ../examples/simple -D CMAKE_TOOLCHAIN_FILE="$( pwd )/../toolchains/mingw-x86.cmake"
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


@contextmanager
def _create_build_dir(args):
    if args.build_dir is not None:
        logging.info('Build directory: %s', args.build_dir)
        yield args.build_dir
        return

    with tempfile.TemporaryDirectory(dir=os.path.dirname(args.src_dir)) as build_dir:
        logging.info('Build directory: %s', build_dir)
        try:
            yield build_dir
        finally:
            logging.info('Removing build directory: %s', build_dir)
        return


class GenerationPhase:
    def __init__(self, build_dir, args):
        self.build_dir = build_dir
        self.args = args

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.args)

    @staticmethod
    def _to_cmake_args(build_dir, args):
        result = []
        if args.install_dir is not None:
            result += ['-D', f'CMAKE_INSTALL_PREFIX={args.install_dir}']
        if args.configuration is not None:
            result += ['-D', f'CMAKE_BUILD_TYPE={args.configuration}']
        if args.cmake_args is not None:
            result += args.cmake_args
        result += [f'-B{build_dir}', f'-H{args.src_dir}']
        return result

    def run(self):
        project.utils.run_cmake(self._cmake_args())


class BuildPhase:
    def __init__(self, build_dir, args):
        self.build_dir = build_dir
        self.args = args

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.args)

    @staticmethod
    def _to_cmake_args(build_dir, args):
        result = ['--build', build_dir]
        if args.configuration is not None:
            result += ['--config', str(args.configuration)]
        if args.install_dir is not None:
            result += ['--target', 'install']
        return result

    def run(self):
        project.utils.run_cmake(self._cmake_args())


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
    parser.add_argument('--configuration', metavar='CONFIG',
                        type=Configuration.parse, default=Configuration.DEBUG,
                        help=f'build configuration ({"/".join(map(str, Configuration))})')
    parser.add_argument('src_dir', metavar='DIR',
                        type=project.utils.normalize_path,
                        help='source directory')
    parser.add_argument('cmake_args', nargs='*', metavar='CMAKE_ARG',
                        help='additional CMake arguments, to be passed verbatim')
    args = parser.parse_args(argv)
    return args


def build(argv=None):
    args = _parse_args(argv)
    with _create_build_dir(args) as build_dir:
        gen_phase = GenerationPhase(build_dir, args)
        gen_phase.run()
        build_phase = BuildPhase(build_dir, args)
        build_phase.run()


def main(argv=None):
    with project.utils.setup_logging():
        build(argv)


if __name__ == '__main__':
    main()
