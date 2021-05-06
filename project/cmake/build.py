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

    $ cmake-build --configuration Release --install path/to/somewhere -- examples/simple
    ...

    $ ./path/to/somewhere/bin/foo
    foo
'''

import argparse
from contextlib import contextmanager
import logging
import os
import sys
import tempfile

from project.configuration import Configuration
from project.platform import Platform
from project.toolset import Toolset, ToolsetHint
from project.utils import normalize_path, mkdir_parent, run, setup_logging


DEFAULT_PLATFORM = Platform.AUTO
DEFAULT_CONFIGURATION = Configuration.DEBUG
DEFAULT_TOOLSET_HINT = ToolsetHint.AUTO


# This way of basically passing `-j` to make is more universal compared to
# _guessing_ that the build system is make and passing -j explicitly.  Plus it
# works with older CMake versions, which don't support the --parallel flag.
cmake_env = os.environ.copy()
cmake_env['CMAKE_BUILD_PARALLEL_LEVEL'] = str(os.cpu_count())


def run_cmake(cmake_args):
    return run(['cmake'] + cmake_args, env=cmake_env)


class GenerationPhase:
    def __init__(self, src_dir, build_dir, install_dir=None, platform=None,
                 configuration=None, boost_dir=None, cmake_args=None):
        src_dir = normalize_path(src_dir)
        build_dir = normalize_path(build_dir)
        if install_dir is not None:
            install_dir = normalize_path(install_dir)
        platform = platform or DEFAULT_PLATFORM
        configuration = configuration or DEFAULT_CONFIGURATION
        if boost_dir is not None:
            boost_dir = normalize_path(boost_dir)
        cmake_args = cmake_args or []

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.install_dir = install_dir
        self.platform = platform
        self.configuration = configuration
        self.boost_dir = boost_dir
        self.cmake_args = cmake_args

    def _cmake_args(self, toolset):
        result = []
        result += toolset.cmake_args(self.build_dir, self.platform)
        result += self.configuration.cmake_args()
        result += self._cmake_boost_args()
        result += self.cmake_args
        # Important! -H must come as the last parameter, older CMake versions
        # don't like it when it's not.
        result += self._cmake_dir_args()
        return result

    def _cmake_boost_args(self):
        if self.boost_dir is None:
            return []
        root = self.boost_dir
        librarydir = self.platform.boost_librarydir(self.configuration)
        librarydir = os.path.join(self.boost_dir, librarydir)
        return [
            '-D', f'BOOST_ROOT={root}',
            '-D', f'BOOST_LIBRARYDIR={librarydir}',
        ]

    def _cmake_dir_args(self):
        args = []
        if self.install_dir is not None:
            args += ['-D', f'CMAKE_INSTALL_PREFIX={self.install_dir}']
        # Important! -H must come as the last parameter, older CMake versions
        # don't like it when it's not.
        args += [
            f'-B{self.build_dir}',
            f'-H{self.src_dir}'
        ]
        return args

    def run(self, toolset):
        run_cmake(self._cmake_args(toolset))


class BuildPhase:
    def __init__(self, build_dir, install_dir=None, configuration=None):

        build_dir = normalize_path(build_dir)
        configuration = configuration or DEFAULT_CONFIGURATION

        self.build_dir = build_dir
        self.install_dir = install_dir
        self.configuration = configuration

    def _cmake_args(self, toolset):
        result = ['--build', self.build_dir]
        result += ['--config', str(self.configuration)]
        if self.install_dir is not None:
            result += ['--target', 'install']
        result += ['--'] + toolset.build_system_args()
        return result

    def run(self, toolset):
        run_cmake(self._cmake_args(toolset))


class BuildParameters:
    def __init__(self, src_dir, build_dir=None, install_dir=None,
                 platform=None, configuration=None, boost_dir=None,
                 toolset_hint=None, cmake_args=None):

        src_dir = normalize_path(src_dir)
        if build_dir is not None:
            build_dir = normalize_path(build_dir)
        if install_dir is not None:
            install_dir = normalize_path(install_dir)
        platform = platform or DEFAULT_PLATFORM
        configuration = configuration or DEFAULT_CONFIGURATION
        if boost_dir is not None:
            boost_dir = normalize_path(boost_dir)
        toolset_hint = toolset_hint or DEFAULT_TOOLSET_HINT
        cmake_args = cmake_args or []

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.install_dir = install_dir
        self.platform = platform
        self.configuration = configuration
        self.boost_dir = boost_dir
        self.toolset_hint = toolset_hint
        self.cmake_args = cmake_args

    @staticmethod
    def from_args(args):
        return BuildParameters(**vars(args))

    @contextmanager
    def create_build_dir(self):
        if self.build_dir is not None:
            logging.info('Build directory: %s', self.build_dir)
            mkdir_parent(self.build_dir)
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
        toolset = Toolset.make(params.toolset_hint, params.platform)

        gen_phase = GenerationPhase(params.src_dir, build_dir,
                                    install_dir=params.install_dir,
                                    platform=params.platform,
                                    configuration=params.configuration,
                                    boost_dir=params.boost_dir,
                                    cmake_args=params.cmake_args)
        gen_phase.run(toolset)
        build_phase = BuildPhase(build_dir, install_dir=params.install_dir,
                                 configuration=params.configuration)
        build_phase.run(toolset)


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

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

    toolset_options = '/'.join(map(str, ToolsetHint.all()))
    parser.add_argument('--toolset', metavar='TOOLSET', dest='toolset_hint',
                        type=ToolsetHint.parse, default=ToolsetHint.AUTO,
                        help=f'toolset to use ({toolset_options})')

    parser.add_argument('src_dir', metavar='DIR',
                        type=normalize_path,
                        help='source directory')
    parser.add_argument('cmake_args', metavar='CMAKE_ARG',
                        nargs='*', default=[],
                        help='additional CMake arguments, to be passed verbatim')

    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    with setup_logging():
        build(BuildParameters.from_args(args))


if __name__ == '__main__':
    main()
