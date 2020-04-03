# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Download & bootstrap Boost.

This script downloads and bootstraps a Boost distribution.  It's main utility
is that it's supposed to be cross-platform.

Usage examples:

    $ python -m project.boost.download 1.71.0
    ...

    $ python -m project.boost.download --unpack ~/workspace/third-party/ 1.65.0
    ...
'''

import argparse
from contextlib import contextmanager
import logging
import sys
import urllib.request

from project.boost.archive import Archive, PermanentStorage, TemporaryStorage
from project.boost.version import Version
from project.utils import normalize_path, retry, setup_logging


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
    def __init__(self, version, unpack_dir=None, cache_dir=None):
        if unpack_dir is None:
            if cache_dir is None:
                unpack_dir = '.'
            else:
                unpack_dir = cache_dir

        self.version = version
        self.unpack_dir = normalize_path(unpack_dir)
        self.storage = TemporaryStorage(unpack_dir)
        if cache_dir is not None:
            cache_dir = normalize_path(cache_dir)
            self.storage = PermanentStorage(cache_dir)

    @staticmethod
    def from_args(args):
        return DownloadParameters(**vars(args))


def download(params):
    with _download_if_necessary(params.version, params.storage) as path:
        archive = Archive(params.version, path)
        boost_dir = archive.unpack(params.unpack_dir)
        boost_dir.bootstrap()


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

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

    return parser.parse_args(argv)


def _main(argv=None):
    with setup_logging():
        download(DownloadParameters.from_args(_parse_args(argv)))


if __name__ == '__main__':
    _main()
