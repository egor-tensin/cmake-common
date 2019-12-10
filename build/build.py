#!/usr/bin/env python3

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This script is used basically to invoke the CMake executable in a
# cross-platform way (provided the platform has Python 3, of course).
# The motivation was to merge my Travis and AppVeyor build scripts (largely
# similar, but written in bash and PowerShell, respectively).

import argparse
from contextlib import contextmanager
import logging
from enum import Enum
import os
import os.path
import shutil
import subprocess
import sys
import tempfile


@contextmanager
def _chdir(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def _make_tmp_dir(**kwargs):
    path = tempfile.mkdtemp(**kwargs)
    logging.info('Created temporary directory: %s', path)
    return path


def _log_rmtree_error(function, path, exc_info):
    logging.error("Couldn't remove path '%s': %s", path, exc_info)


def _remove_dir(path):
    logging.info('Removing directory: %s', path)
    shutil.rmtree(path, onerror=_log_rmtree_error)


def _run_executable(cmd_line):
    logging.info('Running executable: %s', cmd_line)
    result = subprocess.run(cmd_line)
    result.check_returncode()


def _run_cmake(cmake_args):
    _run_executable(['cmake'] + cmake_args)


class Configuration(Enum):
    DEBUG = 'Debug'
    RELEASE = 'Release'

    def __str__(self):
        return self.value


def _parse_configuration(s):
    try:
        return Configuration(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid configuration: {s}')


class BuildDir:
    def __init__(self, args):
        self.path = args.build_dir
        self.clean = args.clean_build_dir
        self.tmp_dir = self.path is None
        if self.tmp_dir:
            self.path = self._make_build_dir()

    @staticmethod
    def _make_build_dir():
        return _make_tmp_dir(prefix='build_')

    def go(self):
        return _chdir(self.path)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.tmp_dir and self.clean:
            _remove_dir(self.path)


class GenerationPhase:
    def __init__(self, build_dir, args):
        self.build_dir = build_dir
        self.args = args

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.args)

    @staticmethod
    def _to_cmake_args(build_dir, args):
        result = []
        if args.generator is not None:
            result += ['-G', args.generator]
        if args.platform is not None:
            result += ['-A', args.platform]
        if args.install_dir is not None:
            result.append(f'-DCMAKE_INSTALL_PREFIX={args.install_dir}')
        if args.configuration is not None:
            result.append(f'-DCMAKE_BUILD_TYPE={args.configuration}')
        if args.toolchain_path is not None:
            result.append(f'-DCMAKE_TOOLCHAIN_FILE={args.toolchain_path}')
        if args.boost_root is not None:
            result.append(f'-DBOOST_ROOT={args.boost_root}')
        if args.boost_librarydir is not None:
            result.append(f'-DBOOST_LIBRARYDIR={args.boost_librarydir}')
        if args.cmake_args is not None:
            result += [arg for arg in args.cmake_args]
        result += [f'-B{build_dir.path}']
        result += [f'-H{args.src_dir}']
        return result

    def run(self):
        _run_cmake(self._cmake_args())


class BuildPhase:
    def __init__(self, build_dir, args):
        self.build_dir = build_dir
        self.args = args

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.args)

    @staticmethod
    def _to_cmake_args(build_dir, args):
        result = ['--build', build_dir.path]
        if args.clean_build_dir:
            result.append('--clean-first')
        if args.configuration is not None:
            result += ['--config', str(args.configuration)]
        if args.install_dir is not None:
            result += ['--target', 'install']
        return result

    def run(self):
        _run_cmake(self._cmake_args())


class CleanPhase:
    def __init__(self, build_dir, args):
        self.build_dir = build_dir
        self.args = args

    def _cmake_args(self):
        return self._to_cmake_args(self.build_dir, self.args)

    @staticmethod
    def _to_cmake_args(build_dir, args):
        result = ['--build', build_dir.path]
        if args.configuration is not None:
            result += ['--config', str(args.configuration)]
        result += ['--target', 'clean']
        return result

    def run(self):
        if self.args.clean_build_dir:
            _run_cmake(self._cmake_args())


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)
    parser = argparse.ArgumentParser(description='Build a CMake project')
    parser.add_argument('--src', required=True, dest='src_dir',
                        type=os.path.abspath, metavar='DIR',
                        help='source directory')
    parser.add_argument('--build', metavar='DIR', dest='build_dir',
                        help='build directory (temporary directory if not specified)')
    parser.add_argument('--install', metavar='DIR', dest='install_dir',
                        help='install directory')
    parser.add_argument('--clean', action='store_true', dest='clean_build_dir',
                        help='clean the build directory (temporary directory will be removed)')
    parser.add_argument('--generator', help='build system to use')
    parser.add_argument('--platform', help='target platform (i.e. Win32/x64)')
    parser.add_argument('--configuration', metavar='CONFIG',
                        type=_parse_configuration,
                        help='build configuration (i.e. Debug/Release)')
    parser.add_argument('--toolchain', metavar='PATH', dest='toolchain_path',
                        help='CMake toolchain file path')
    parser.add_argument('--boost', metavar='DIR', dest='boost_root',
                        help='set Boost directory')
    parser.add_argument('--boost-librarydir', metavar='DIR',
                        help='set Boost library directory (stage/lib by default)')
    parser.add_argument('cmake_args', nargs='*', metavar='CMAKE_ARG',
                        help='additional CMake arguments, to be passed verbatim')
    args = parser.parse_args(argv)
    return args


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def build(argv=None):
    args = _parse_args(argv)
    with BuildDir(args) as build_dir:
        gen_phase = GenerationPhase(build_dir, args)
        gen_phase.run()
        build_phase = BuildPhase(build_dir, args)
        build_phase.run()
        clean_phase = CleanPhase(build_dir, args)
        clean_phase.run()


def main(argv=None):
    _setup_logging()
    try:
        build(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
