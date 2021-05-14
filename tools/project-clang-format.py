#!/usr/bin/env python3

# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''clang-format all C/C++ files in the project

This script feeds every C/C++ file in the repository to clang-format, either
printing a unified diff between the original and the formatted versions, or
formatting the files in-place.
'''

import argparse
from contextlib import contextmanager
import difflib
import logging
import os
import subprocess
import sys


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
        sys.exit(1)


@contextmanager
def cd(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def normalize_path(entry):
    return os.path.abspath(entry)


def run(cmd_line):
    logging.debug('Running executable: %s', cmd_line)
    try:
        return subprocess.run(cmd_line, check=True, universal_newlines=True,
                              stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logging.error('Process finished with exit code %d: %s', e.returncode, cmd_line)
        logging.error('Its output was:\n%s', e.output)
        raise


def read_file(path):
    with open(path) as file:
        return file.read()


class ClangFormat:
    def __init__(self, path, style):
        self.path = path
        self.style = style

    def _get_command_line(self, paths, in_place=False):
        cmd_line = [self.path, f'-style={self.style}']
        if in_place:
            cmd_line.append('-i')
        cmd_line.append('--')
        cmd_line += list(paths)
        return cmd_line

    def format_in_place(self, paths):
        run(self._get_command_line(paths, in_place=True))

    @staticmethod
    def _show_diff(path, formatted):
        original = read_file(path).split('\n')
        formatted = formatted.split('\n')
        original_lbl = f'{path} (original)'
        formatted_lbl = f'{path} (formatted)'

        diff = difflib.unified_diff(original, formatted, fromfile=original_lbl,
                                    tofile=formatted_lbl, lineterm='')

        clean = True
        for line in diff:
            clean = False
            print(line)
        return clean

    def show_diff(self, paths):
        clean = True
        for path in paths:
            formatted = run(self._get_command_line([path])).stdout
            clean = self._show_diff(path, formatted) and clean
        return clean


def git_root_dir():
    cmd_line = ['git', 'rev-parse', '--show-toplevel']
    root_dir = run(cmd_line).stdout
    if root_dir[-1] != '\n':
        raise RuntimeError('git rev-parse --show-toplevel should append a newline?')
    return root_dir[:-1]


def list_git_files():
    cmd_line = ['git', 'ls-tree', '-r', '-z', '--name-only', 'HEAD']
    repo_files = run(cmd_line).stdout
    repo_files = repo_files.split('\0')
    return repo_files


def list_all_files():
    return (normalize_path(path) for path in list_git_files())


def excluded(path, exclude):
    for entry in exclude:
        if entry == os.path.commonpath((path, entry)):
            return True
    return False


def filter_files(paths, exclude):
    if not exclude:
        return paths
    return (path for path in paths if not excluded(path, exclude))


CPP_FILE_EXTENSIONS = set(('.c', '.h', '.cc', '.hh', '.cpp', '.hpp', '.cxx', '.hxx', '.cp', '.c++'))


def list_cpp_files():
    for path in list_all_files():
        ext = os.path.splitext(path)[1].lower()
        if ext in CPP_FILE_EXTENSIONS:
            yield path


DEFAULT_VERSION = 'clang-format'
DEFAULT_STYLE = 'file'


def process_cpp_files(version=DEFAULT_VERSION, style=DEFAULT_STYLE,
                      in_place=False, exclude=None):
    clang_format = ClangFormat(version, style)
    with cd(git_root_dir()):
        cpp_files = filter_files(list_cpp_files(), exclude)
        if in_place:
            clang_format.format_in_place(cpp_files)
        else:
            if not clang_format.show_diff(cpp_files):
                sys.exit(1)


def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-b', '--clang-format', dest='version',
                        default=DEFAULT_VERSION,
                        help='clang-format executable file path')
    parser.add_argument('-s', '--style', default=DEFAULT_STYLE,
                        help='clang-format -style parameter argument')
    parser.add_argument('-i', '--in-place', action='store_true',
                        help='edit the files in-place')
    parser.add_argument('-e', '--exclude', nargs='*', type=normalize_path,
                        help='files or directories to exclude')

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    with setup_logging():
        process_cpp_files(**vars(args))


if __name__ == '__main__':
    main()
