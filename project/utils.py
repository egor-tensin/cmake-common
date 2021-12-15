# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from contextlib import contextmanager
import functools
import logging
import os.path
import shutil
import subprocess
import sys
import tempfile
import time

import project.os


def normalize_path(s):
    return os.path.abspath(os.path.normpath(s))


def mkdir_parent(path):
    os.makedirs(path, exist_ok=True)


def full_exe_name(exe):
    if not project.os.on_windows_like():
        # There's no PATHEXT on Linux.
        return exe
    # b2 on Windows/Cygwin doesn't like it when the executable name doesn't
    # include the extension.
    dir_path = os.path.dirname(exe) or None
    path = shutil.which(exe, path=dir_path)
    if not path:
        raise RuntimeError(f"executable '{exe}' could not be found")
    if project.os.on_cygwin():
        # On Cygwin, shutil.which('gcc') == '/usr/bin/gcc' and shutil.which('gcc.exe')
        # == '/usr/bin/gcc.exe'; we want the latter version.  shutil.which('clang++')
        # == '/usr/bin/clang++' is fine though, since it _is_ the complete path
        # (clang++ is a symlink).
        if os.path.exists(path) and os.path.exists(path + '.exe'):
            path += '.exe'
    if dir_path:
        # If it was found in a specific directory, include the directory in the
        # result.  shutil.which returns the executable name prefixed with the
        # path argument.
        return path
    # If it was found in PATH, just return the basename (which includes the
    # extension).
    return os.path.basename(path)


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
        sys.exit(1)


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


def retry(exc_type, timeout=5, tries=3, backoff=2):
    def wrapper(func):
        @functools.wraps(func)
        def func2(*args, **kwargs):
            current_timeout = timeout
            current_try = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exc_type as e:
                    logging.exception(e)
                    current_try += 1
                    if current_try < tries:
                        logging.error('Retrying after %d seconds', current_timeout)
                        time.sleep(current_timeout)
                        current_timeout *= backoff
                        continue
                    raise
        return func2
    return wrapper
