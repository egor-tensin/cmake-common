#!/usr/bin/env python3

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This script downloads and builds the Boost libraries.

import argparse
from contextlib import contextmanager
from enum import Enum
import logging
import os.path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request


@contextmanager
def _chdir(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def _on_windows():
    return platform.system() == 'Windows'


def _run_executable(cmd_line):
    logging.info('Running executable: %s', cmd_line)
    result = subprocess.run(cmd_line)
    result.check_returncode()


class Platform(Enum):
    X86 = 'x86'
    X64 = 'x64'
    WIN32 = 'Win32'

    def __str__(self):
        return self.value

    @staticmethod
    def all():
        return (Platform.X86, Platform.X64)

    def get_address_model(self):
        if self is Platform.X86:
            return 32
        if self is Platform.X64:
            return 64
        if self is Platform.WIN32:
            return 32
        raise NotImplementedError(f'unsupported platform: {self}')


def _parse_platform(s):
    try:
        return Platform(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid platform: {s}')


class Configuration(Enum):
    DEBUG = 'Debug'
    RELEASE = 'Release'

    @staticmethod
    def all():
        return tuple(Configuration)

    def __str__(self):
        return self.value


def _parse_configuration(s):
    try:
        return Configuration(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid configuration: {s}')


class Linkage(Enum):
    STATIC = 'static'
    SHARED = 'shared'

    @staticmethod
    def all():
        return tuple(Linkage)

    def __str__(self):
        return self.value


def _parse_linkage(s):
    try:
        return Linkage(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid linkage settings: {s}')


class BoostVersion:
    def __init__(self, major, minor, patch):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self):
        return f'{self.major}.{self.minor}.{self.patch}'

    @property
    def archive_ext(self):
        return '.tar.gz'

    def dir_path(self, parent_dir):
        return os.path.join(parent_dir, self.dir_name)

    @property
    def dir_name(self):
        return f'boost_{self.major}_{self.minor}_{self.patch}'

    @property
    def archive_name(self):
        return f'{self.dir_name}{self.archive_ext}'

    def get_download_url(self):
        return f'https://dl.bintray.com/boostorg/release/{self}/source/{self.archive_name}'


def _parse_boost_version(s):
    result = re.match(r'^(\d+)\.(\d+)\.(\d+)$', s)
    if result is None:
        raise argparse.ArgumentTypeError(f'invalid Boost version: {s}')
    return BoostVersion(result.group(1), result.group(2), result.group(3))


class BoostArchive:
    def __init__(self, version, path):
        self.version = version
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logging.info('Removing temporary file: %s', self.path)
        os.remove(self.path)

    @property
    def dir_name(self):
        return self.version.dir_name

    @staticmethod
    def download(version):
        path = None
        with tempfile.NamedTemporaryFile(prefix='boost_', suffix=version.archive_ext, delete=False) as dest:
            path = dest.name
            logging.info('Downloading Boost to: %s', path)
            url = version.get_download_url()
            logging.info('Download URL: %s', url)

            with urllib.request.urlopen(url) as request:
                dest.write(request.read())
        return BoostArchive(version, path)


class BoostDir:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise RuntimeError(f"Boost directory doesn't exist: {path}")
        self.path = path

    @staticmethod
    def unpack(archive, dest):
        path = os.path.join(dest, archive.dir_name)
        if os.path.exists(path):
            raise RuntimeError(f'Boost directory already exists: {path}')
        logging.info('Unpacking Boost to: %s', path)
        shutil.unpack_archive(archive.path, dest)
        return BoostDir(path)

    def _go(self):
        return _chdir(self.path)

    def build(self, params):
        with self._go():
            self._bootstrap_if_required()
            self._b2(params)

    def _bootstrap_if_required(self):
        if os.path.isfile(self._b2_path()):
            logging.info('Not going to bootstrap, b2 is already there')
            return
        self._bootstrap()

    def _bootstrap(self):
        _run_executable(self._bootstrap_path())

    def _b2(self, params):
        for b2_params in params.enum_b2_params():
            _run_executable([self._b2_path()] + b2_params)

    @staticmethod
    def _bootstrap_path():
        return os.path.join('.', BoostDir._bootstrap_name())

    @staticmethod
    def _bootstrap_name():
        ext = '.sh'
        if _on_windows():
            ext = '.bat'
        return f'bootstrap{ext}'

    @staticmethod
    def _b2_path():
        return os.path.join('.', BoostDir._b2_name())

    @staticmethod
    def _b2_name():
        ext = ''
        if _on_windows():
            ext = '.exe'
        return f'b2{ext}'


class BoostBuild:
    def __init__(self, args):
        self.platforms = args.platforms or Platform.all()
        self.configurations = args.configurations or Configuration.all()
        self.runtime_link = args.runtime_link or Linkage.all()
        self.link = args.link or Linkage.all()
        self.libraries = args.libraries
        self.b2_args = args.b2_args

    def enum_b2_params(self):
        for platform in self.platforms:
            platform_params = []
            platform_params.append(self._address_model(platform))
            platform_params.append(self._runtime_link())
            platform_params.append(self._link())
            platform_params += self._with_optional()
            platform_params += self.b2_args
            if _on_windows():
                platform_params.append(self._windows_stagedir(platform))
                platform_params.append(self._windows_variant(self.configurations))
                yield platform_params
            else:
                for configuration in self.configurations:
                    variant_params = list(platform_params)
                    variant_params.append(self._unix_stagedir(platform, configuration))
                    variant_params.append(self._unix_variant(configuration))
                    yield variant_params

    @staticmethod
    def _address_model(platform):
        return f'address-model={platform.get_address_model()}'

    def _runtime_link(self):
        link = ','.join(map(str, self.runtime_link))
        return f'runtime-link={link}'

    def _link(self):
        link = ','.join(map(str, self.link))
        return f'link={link}'

    def _with_optional(self):
        return [f'--with-{lib}' for lib in self.libraries]

    @staticmethod
    def _windows_stagedir(platform):
        return f'--stagedir=stage/{platform}'

    @staticmethod
    def _unix_stagedir(platform, configuration):
        return f'--stagedir=stage/{platform}/{configuration}'

    @staticmethod
    def _windows_variant(configurations):
        variant = ','.join((str(config).lower() for config in configurations))
        return f'variant={variant}'

    @staticmethod
    def _unix_variant(configuration):
        return f'variant={str(configuration).lower()}'


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', metavar='VERSION', dest='boost_version',
                        type=_parse_boost_version, required=True,
                        help='Boost version (in the MAJOR.MINOR.PATCH format)')
    parser.add_argument('--no-download', action='store_true',
                        help="don't download Boost, attempt to build the existing directory")
    parser.add_argument('--platform', metavar='PLATFORM',
                        nargs='*', dest='platforms', default=(),
                        type=_parse_platform,
                        help='target platform (e.g. x86/x64)')
    parser.add_argument('--configuration', metavar='CONFIGURATION',
                        nargs='*', dest='configurations', default=(),
                        type=_parse_configuration,
                        help='target platform (e.g. Debug/Release)')
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        nargs='*', dest='runtime_link', default=(),
                        type=_parse_linkage,
                        help='runtime linkage options (e.g. static/shared)')
    parser.add_argument('--link', metavar='LINKAGE',
                        nargs='*', dest='link', default=(),
                        type=_parse_linkage,
                        help='library linkage options (e.g. static/shared)')
    parser.add_argument('--build', metavar='DIR', dest='build_dir',
                        type=os.path.abspath, default='.',
                        help='destination directory')
    parser.add_argument('--with', metavar='LIB', dest='libraries',
                        nargs='*', default=(),
                        help='only build these libraries')
    parser.add_argument('b2_args', nargs='*', metavar='B2_ARG', default=(),
                        help='additional b2 arguments, to be passed verbatim')
    return parser.parse_args(argv)


def _build(boost_dir, build_params):
    boost_dir.build(build_params)


def download_and_build(argv=None):
    args = _parse_args(argv)
    build_params = BoostBuild(args)
    if args.no_download:
        boost_dir = BoostDir(args.boost_version.dir_path(args.build_dir))
        _build(boost_dir, build_params)
    else:
        with BoostArchive.download(args.boost_version) as archive:
            boost_dir = BoostDir.unpack(archive, args.build_dir)
            _build(boost_dir, build_params)


def main(argv=None):
    _setup_logging()
    try:
        download_and_build(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
