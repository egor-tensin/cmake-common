# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import abc
from contextlib import contextmanager
import logging
import os.path
import shutil

from project.boost.directory import BoostDir
from project.utils import temp_file


class Archive:
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
    @abc.abstractmethod
    def get_archive(self, version):
        pass

    @contextmanager
    @abc.abstractmethod
    def write_archive(self, version, contents):
        pass


class PermanentStorage(ArchiveStorage):
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


class TemporaryStorage(ArchiveStorage):
    def __init__(self, temp_dir):
        self._dir = temp_dir

    def get_archive(self, version):
        return None

    @contextmanager
    def write_archive(self, version, contents):
        tmp = temp_file(prefix=f'boost_{version}_',
                        suffix=version.archive_ext, dir=self._dir)
        with tmp as archive_path:
            with open(archive_path, mode='wb') as fd:
                fd.write(contents)
            yield archive_path
