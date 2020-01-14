#!/usr/bin/env python3

# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''Feed C/C++ files in the repository to clang-format

This script runs clang-format on every C/C++ file in the repository, either
printing a unified diff between the original and the formatted versions, or
formatting the files in-place.
'''

import argparse
import difflib
import logging
import os.path
import subprocess
import sys


def _setup_logging():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)


def _run_executable(cmd_line):
    logging.debug('Running executable: %s', cmd_line)
    try:
        return subprocess.run(cmd_line, check=True, universal_newlines=True,
                              stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logging.error('Process finished with exit code %d: %s', e.returncode, cmd_line)
        logging.error('Its output was:\n%s', e.output)
        raise


def _read_file(path):
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
        _run_executable(self._get_command_line(paths, in_place=True))

    @staticmethod
    def _show_diff(path, formatted):
        original = _read_file(path).split('\n')
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
            formatted = _run_executable(self._get_command_line([path])).stdout
            clean = self._show_diff(path, formatted) and clean
        return clean


def _list_all_files():
    cmd_line = ['git', 'ls-tree', '-r', '-z', '--name-only', 'HEAD']
    repo_files = _run_executable(cmd_line).stdout
    repo_files = repo_files.split('\0')
    return repo_files


CPP_FILE_EXTENSIONS = {'.c', '.h', '.cc', '.hh', '.cpp', '.hpp', '.cxx', '.hxx', '.cp', '.c++'}


def _list_cpp_files():
    for path in _list_all_files():
        ext = os.path.splitext(path)[1]
        if ext in CPP_FILE_EXTENSIONS:
            yield path


def _process_cpp_files(args):
    clang_format = ClangFormat(args.clang_format, args.style)
    cpp_files = _list_cpp_files()
    if args.in_place:
        clang_format.format_in_place(cpp_files)
    else:
        if not clang_format.show_diff(cpp_files):
            sys.exit(1)


DEFAULT_CLANG_FORMAT = 'clang-format'
DEFAULT_STYLE = 'file'


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-b', '--clang-format', default=DEFAULT_CLANG_FORMAT,
                        help='clang-format executable file path')
    parser.add_argument('-s', '--style', default=DEFAULT_STYLE,
                        help='clang-format -style parameter argument')
    parser.add_argument('-i', '--in-place', action='store_true',
                        help='edit the files in-place')

    return parser.parse_args(argv)


def main(argv=None):
    _setup_logging()
    try:
        args = _parse_args(argv)
        _process_cpp_files(args)
    except Exception as e:
        logging.exception(e)
        raise


if __name__ == '__main__':
    main()
