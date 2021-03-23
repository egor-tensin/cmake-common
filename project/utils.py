# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from contextlib import contextmanager
import functools
import logging
import os.path
import subprocess
import sys
import tempfile
import time


def normalize_path(s):
    return os.path.abspath(os.path.normpath(s))


def mkdir_parent(path):
    os.makedirs(path, exist_ok=True)


@contextmanager
def setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
        # Log to stdout, because that's where subprocess's output goes (so that
        # they don't get interleaved).
        stream=sys.stdout)
    try:
        yield
    except Exception as e:
        logging.exception(e)
        raise


@contextmanager
def cd(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def run(cmd_line, **kwargs):
    logging.info('Running executable: %s', cmd_line)
    return subprocess.run(cmd_line, check=True, **kwargs)


@contextmanager
def delete_on_error(path):
    try:
        yield
    except:
        logging.info('Removing temporary file: %s', path)
        os.remove(path)
        raise


@contextmanager
def delete(path):
    try:
        yield
    finally:
        logging.info('Removing temporary file: %s', path)
        os.remove(path)


@contextmanager
def temp_file(**kwargs):
    '''Make NamedTemporaryFile usable on Windows.

    It can't be opened a second time on Windows, hence this silliness.
    '''
    tmp = tempfile.NamedTemporaryFile(delete=False, **kwargs)
    with tmp as file, delete_on_error(file.name):
        path = file.name
        logging.info('Created temporary file: %s', path)
    with delete(path):
        yield path


def env(name):
    if name not in os.environ:
        raise RuntimeError(f'undefined environment variable: {name}')
    return os.environ[name]


def retry(exc_type, timeout=5, retries=3, backoff=2):
    def wrapper(func):
        @functools.wraps(func)
        def func2(*args, **kwargs):
            current_timeout = timeout
            for retry_n in range(retries):
                try:
                    return func(*args, **kwargs)
                except exc_type as e:
                    logging.exception(e)
                    if retry_n < retries:
                        logging.error('Retrying after %d seconds', current_timeout)
                        time.sleep(current_timeout)
                        current_timeout *= backoff
                        continue
                    raise
        return func2
    return wrapper
