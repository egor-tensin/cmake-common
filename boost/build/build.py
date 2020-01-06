#!/usr/bin/env python3

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This script downloads and builds the Boost libraries.
# It's main utility is being able to download & unpack the Boost distribution
# archive in a cross-platform way + setting the correct --stagedir parameter
# value to avoid name clashes.

import abc
import argparse
from collections import namedtuple
from contextlib import contextmanager
from enum import Enum
from functools import total_ordering
import logging
import os.path
import platform
import re
import shutil
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
    return subprocess.run(cmd_line, check=True)


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


class Link(Enum):
    STATIC = 'static'
    SHARED = 'shared'

    @staticmethod
    def all():
        return tuple(Link)

    def __str__(self):
        return self.value


def _parse_link(s):
    try:
        return Link(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid linkage: {s}')


Version = namedtuple('Version', ['major', 'minor', 'patch'])


@total_ordering
class BoostVersion:
    def __init__(self, major, minor, patch):
        self._impl = Version(major, minor, patch)

    @property
    def major(self):
        return self._impl.major

    @property
    def minor(self):
        return self._impl.minor

    @property
    def patch(self):
        return self._impl.patch

    def __lt__(self, other):
        return self._impl < other._impl

    def __eq__(self, other):
        return self._impl == other._impl

    @staticmethod
    def from_string(s):
        result = re.match(r'^(\d+)\.(\d+)\.(\d+)$', s)
        if result is None:
            raise ValueError(f'invalid Boost version: {s}')
        major = int(result.group(1))
        minor = int(result.group(2))
        patch = int(result.group(3))
        return BoostVersion(major, minor, patch)

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
        if self._impl < Version(1, 63, 0):
            return f'https://sourceforge.net/projects/boost/files/boost/{self}/{self.archive_name}/download'
        return f'https://dl.bintray.com/boostorg/release/{self}/source/{self.archive_name}'


class BoostArchive:
    def __init__(self, version, path):
        self.version = version
        self.path = path

    @property
    def dir_name(self):
        return self.version.dir_name

    def unpack(self, dest_dir):
        path = os.path.join(dest_dir, self.dir_name)
        if os.path.exists(path):
            raise RuntimeError(f'Boost directory already exists: {path}')
        logging.info('Unpacking Boost to: %s', path)
        shutil.unpack_archive(self.path, dest_dir)
        return BoostDir(path)


class ArchiveStorage(abc.ABC):
    @contextmanager
    def download(self, version):
        path = self.get_archive(version)
        if path is not None:
            logging.info('Using existing Boost archive: %s', path)
            yield BoostArchive(version, path)
            return

        url = version.get_download_url()
        logging.info('Download URL: %s', url)

        with urllib.request.urlopen(url) as request:
            with self.write_archive(version, request.read()) as path:
                yield BoostArchive(version, path)

    @abc.abstractmethod
    def get_archive(self, version):
        pass

    @contextmanager
    @abc.abstractmethod
    def write_archive(self, version, contents):
        pass


class CacheStorage(ArchiveStorage):
    def __init__(self, cache_dir):
        self._dir = cache_dir

    def _archive_path(self, version):
        return os.path.join(self._dir, version.archive_name)

    def get_archive(self, version):
        path = self._archive_path(version)
        if os.path.exists(path):
            return path
        return None

    @contextmanager
    def write_archive(self, version, contents):
        path = self._archive_path(version)
        logging.info('Writing Boost archive: %s', path)
        if os.path.exists(path):
            raise RuntimeError(f'cannot download Boost, file already exists: {path}')
        with open(path, mode='w+b') as dest:
            dest.write(contents)
        yield path


class TempStorage(ArchiveStorage):
    def __init__(self, temp_dir):
        self._dir = temp_dir

    def get_archive(self, version):
        return None

    @contextmanager
    def write_archive(self, version, contents):
        with tempfile.NamedTemporaryFile(prefix=f'boost_{version}_', suffix=version.archive_ext, dir=self._dir, delete=False) as dest:
            path = dest.name
            logging.info('Writing Boost archive: %s', path)
            dest.write(contents)
        try:
            yield path
        finally:
            logging.info('Removing temporary Boost archive: %s', path)
            os.remove(path)


class BoostDir:
    def __init__(self, path):
        if not os.path.isdir(path):
            raise RuntimeError(f"Boost directory doesn't exist: {path}")
        self.path = path

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
        self.bootstrap()

    def bootstrap(self):
        with self._go():
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
        self.link = args.link or Link.all()

        self.stage_dir = 'stage'

        self.build_dir = args.build_dir
        self.boost_dir = args.boost_dir

        self.b2_args = args.b2_args

    def enum_b2_params(self):
        with self._create_build_dir() as build_dir:
            for platform in self.platforms:
                platform_params = [f'--build-dir={build_dir}']
                platform_params.append(self._address_model(platform))
                platform_params.append(self._linkage())
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

    @contextmanager
    def _create_build_dir(self):
        if self.build_dir is not None:
            logging.info('Build directory: %s', self.build_dir)
            yield self.build_dir
            return

        with tempfile.TemporaryDirectory(dir=os.path.dirname(self.boost_dir)) as build_dir:
            logging.info('Build directory: %s', build_dir)
            try:
                yield build_dir
            finally:
                logging.info('Removing build directory: %s', build_dir)
            return

    def _linkage(self):
        link = ','.join(map(str, self.link))
        return f'link={link}'

    @staticmethod
    def _address_model(platform):
        return f'address-model={platform.get_address_model()}'

    def _windows_stagedir(self, platform):
        return f'--stagedir={os.path.join(self.stage_dir, str(platform))}'

    def _unix_stagedir(self, platform, configuration):
        return f'--stagedir={os.path.join(self.stage_dir, str(platform), str(configuration))}'

    @staticmethod
    def _windows_variant(configurations):
        variant = ','.join((str(config).lower() for config in configurations))
        return f'variant={variant}'

    @staticmethod
    def _unix_variant(configuration):
        return f'variant={str(configuration).lower()}'


def _parse_dir(s):
    return os.path.abspath(os.path.normpath(s))


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    download = subparsers.add_parser('download', help='download & bootstrap Boost')

    download.add_argument('--cache', metavar='DIR', dest='cache_dir',
                          type=_parse_dir,
                          help='download directory (temporary file unless specified)')
    download.add_argument('--unpack', metavar='DIR', dest='unpack_dir',
                          type=_parse_dir, default='.',
                          help='directory to unpack Boost to')
    download.add_argument('boost_version', metavar='VERSION',
                          type=BoostVersion.from_string,
                          help='Boost version (in the MAJOR.MINOR.PATCH format)')

    build = subparsers.add_parser('build', help='build Boost libraries')

    # These are used to put the built libraries into proper stage/
    # subdirectories (to avoid name clashes).
    build.add_argument('--platform', metavar='PLATFORM',
                       nargs='*', dest='platforms', default=[],
                       type=_parse_platform,
                       help='target platform (e.g. x86/x64)')
    build.add_argument('--configuration', metavar='CONFIGURATION',
                       nargs='*', dest='configurations', default=[],
                       type=_parse_configuration,
                       help='target configuration (e.g. Debug/Release)')
    # This is needed because the default behaviour on Linux and Windows is
    # different: static & dynamic libs are built on Linux, but only static libs
    # are built on Windows by default.
    build.add_argument('--link', metavar='LINKAGE',
                       nargs='*', default=[],
                       type=_parse_link,
                       help='how the libraries are linked (i.e. static/shared)')

    build.add_argument('--build', metavar='DIR', dest='build_dir',
                       type=_parse_dir,
                       help='Boost build directory (temporary directory unless specified)')
    build.add_argument('boost_dir', metavar='DIR',
                       type=_parse_dir,
                       help='root Boost directory')

    build.add_argument('b2_args', nargs='*', metavar='B2_ARG', default=[],
                       help='additional b2 arguments, to be passed verbatim')

    return parser.parse_args(argv)


def build(args):
    build_params = BoostBuild(args)
    boost_dir = BoostDir(args.boost_dir)
    boost_dir.build(build_params)


def download(args):
    storage = TempStorage(args.unpack_dir)
    if args.cache_dir is not None:
        storage = CacheStorage(args.cache_dir)
    with storage.download(args.boost_version) as archive:
        boost_dir = archive.unpack(args.unpack_dir)
        boost_dir.bootstrap()


def main(argv=None):
    args = _parse_args(argv)
    if args.command == 'download':
        download(args)
    elif args.command == 'build':
        build(args)
    else:
        raise NotImplementedError(f'unsupported command: {args.command}')


def _main(argv=None):
    _setup_logging()
    try:
        main(argv)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    _main()
