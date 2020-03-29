# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from contextlib import contextmanager
import logging
import os.path
import subprocess
import tempfile


def normalize_path(s):
    return os.path.abspath(os.path.normpath(s))


@contextmanager
def setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)
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


def run(cmd_line):
    logging.info('Running executable: %s', cmd_line)
    return subprocess.run(cmd_line, check=True)


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
def temp_file(contents, **kwargs):
    '''Make NamedTemporaryFile usable on Windows.

    It can't be opened a second time on Windows, hence this silliness.
    '''
    tmp = tempfile.NamedTemporaryFile(delete=False, **kwargs)
    with tmp as file, delete_on_error(file.name):
        path = file.name
        logging.info('Writing temporary file: %s', path)
        file.write(contents)
    with delete(path):
        yield path
