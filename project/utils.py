# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from contextlib import contextmanager
import logging
import os.path
import subprocess


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


def run_cmake(cmake_args):
    return run(['cmake'] + cmake_args)
