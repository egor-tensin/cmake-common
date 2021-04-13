# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Download & bootstrap Boost.

This script downloads and unpacks a Boost distribution archive.  Its main
utility is that it's supposed to be cross-platform.

Usage examples:

    $ boost-download 1.71.0
    ...

    $ boost-download --unpack ~/workspace/third-party/ 1.65.0
    ...
'''

import argparse
from contextlib import contextmanager
import logging
import os
import sys
import urllib.request

from project.boost.archive import Archive, PermanentStorage, TemporaryStorage
from project.boost.version import Version
from project.utils import normalize_path, mkdir_parent, retry, setup_logging


@retry(urllib.request.URLError)
def _download_try_url_retry(url):
    with urllib.request.urlopen(url, timeout=20) as request:
        return request.read()


def _download_try_url(url):
    logging.info('Trying URL: %s', url)
    try:
        return _download_try_url_retry(url)
    except urllib.request.URLError as e:
        logging.error("Couldn't download from this mirror, an error occured:")
        logging.exception(e)


@contextmanager
def _download_try_all_urls(version, storage):
    urls = version.get_download_urls()
    for url in urls:
        reply = _download_try_url(url)
        if reply is None:
            continue
        with storage.write_archive(version, reply) as path:
            yield path
            return
    raise RuntimeError("Couldn't download Boost from any of the mirrors")


@contextmanager
def _download_if_necessary(version, storage):
    path = storage.get_archive(version)
    if path is not None:
        logging.info('Using existing Boost archive: %s', path)
        yield path
        return
    with _download_try_all_urls(version, storage) as path:
        yield path


class DownloadParameters:
    def __init__(self, version, unpack_dir=None, cache_dir=None, dest_path=None):
        if unpack_dir is None:
            if cache_dir is None:
                unpack_dir = '.'
            else:
                unpack_dir = cache_dir

        unpack_dir = normalize_path(unpack_dir)
        mkdir_parent(unpack_dir)
        if cache_dir is not None:
            cache_dir = normalize_path(cache_dir)
            mkdir_parent(cache_dir)

        self.version = version
        self.unpack_dir = unpack_dir
        if cache_dir is None:
            self.storage = TemporaryStorage(unpack_dir)
        else:
            self.storage = PermanentStorage(cache_dir)
        self.dest_path = dest_path

    @staticmethod
    def from_args(args):
        return DownloadParameters(**vars(args))

    def rename_if_necessary(self, boost_dir):
        if self.dest_path is not None:
            os.rename(boost_dir.path, self.dest_path)


def download(params):
    with _download_if_necessary(params.version, params.storage) as path:
        archive = Archive(params.version, path)
        boost_dir = archive.unpack(params.unpack_dir)
        params.rename_if_necessary(boost_dir)


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--unpack', metavar='DIR', dest='unpack_dir',
                        type=normalize_path,
                        help='directory to unpack the archive to')
    parser.add_argument('--cache', metavar='DIR', dest='cache_dir',
                        type=normalize_path,
                        help='download directory (temporary file unless specified)')
    parser.add_argument('version', metavar='VERSION',
                        type=Version.from_string,
                        help='Boost version (in the MAJOR.MINOR.PATCH format)')
    parser.add_argument('dest_path', metavar='DIR', nargs='?',
                        type=normalize_path,
                        help='rename the boost directory to DIR')

    return parser.parse_args(argv)


def _main(argv=None):
    args = _parse_args(argv)
    with setup_logging():
        download(DownloadParameters.from_args(args))


if __name__ == '__main__':
    _main()
