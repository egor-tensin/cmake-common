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
import project.version


class Download:
    def __init__(self, version, unpack_dir=None, cache_dir=None,
                 dest_path=None, no_retry=False):
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
        self.no_retry = no_retry

    @staticmethod
    def from_args(args):
        return Download(**vars(args))

    def rename_if_necessary(self, boost_dir):
        if self.dest_path is not None:
            os.rename(boost_dir.path, self.dest_path)

    @staticmethod
    def _download_url(url):
        with urllib.request.urlopen(url, timeout=20) as request:
            return request.read()

    @staticmethod
    @retry(urllib.request.URLError)
    def _download_url_retry(url):
        return Download._download_url(url)

    def _try_url(self, url):
        logging.info('Trying URL: %s', url)
        try:
            if self.no_retry:
                return self._download_url(url)
            return self._download_url_retry(url)
        except urllib.request.URLError as e:
            logging.error("Couldn't download from this mirror, an error occured:")
            logging.exception(e)
            return None

    def _try_urls(self):
        urls = self.version.get_download_urls()
        for url in urls:
            reply = self._try_url(url)
            if self.no_retry:
                break
            if reply is not None:
                break
        if reply is None:
            raise RuntimeError("Couldn't download Boost from any of the mirrors")
        return reply

    @contextmanager
    def _download_from_cdn(self):
        reply = self._try_urls()
        with self.storage.write_archive(self.version, reply) as path:
            yield path
            return

    @contextmanager
    def download_if_necessary(self):
        path = self.storage.get_archive(self.version)
        if path is not None:
            logging.info('Using existing Boost archive: %s', path)
            yield path
            return
        with self._download_from_cdn() as path:
            yield path


def download(params):
    with params.download_if_necessary() as path:
        archive = Archive(params.version, path)
        boost_dir = archive.unpack(params.unpack_dir)
        params.rename_if_necessary(boost_dir)


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    project.version.add_to_arg_parser(parser)

    parser.add_argument('--unpack', metavar='DIR', dest='unpack_dir',
                        type=normalize_path,
                        help='directory to unpack the archive to')
    parser.add_argument('--cache', metavar='DIR', dest='cache_dir',
                        type=normalize_path,
                        help='download directory (temporary file unless specified)')
    parser.add_argument('--no-retry', action='store_true',
                        help=argparse.SUPPRESS)
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
        download(Download.from_args(args))


if __name__ == '__main__':
    _main()
