#!/usr/bin/env python3

# Copyright (c) 2021 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''Wrap your actual test driver to use with CTest

CTest suffers from at least two issues, in particular with regard to its
PASS_REGULAR_EXPRESSION feature:

1. The regular expression syntax used by CMake is deficient.
2. The exit code of a test is ignored if one of the regexes matches.

This script tries to fix them.
'''

import argparse
import os
import re
import subprocess
import sys


SCRIPT_NAME = os.path.basename(__file__)


def dump(msg, **kwargs):
    print(f'{SCRIPT_NAME}: {msg}', **kwargs)


def err(msg):
    dump(msg, file=sys.stderr)


def read_file(path):
    with open(path, mode='r') as fd:
        return fd.read()


def run(cmd_line):
    try:
        result = subprocess.run(cmd_line, check=True, universal_newlines=True,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE)
        assert result.returncode == 0
        return result.stdout
    except subprocess.CalledProcessError as e:
        sys.stdout.write(e.output)
        sys.exit(e.returncode)


def run_new_window(cmd_line):
    try:
        result = subprocess.run(cmd_line, check=True,
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
        assert result.returncode == 0
        return None
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def match(s, regex):
    return re.search(regex, s, flags=re.MULTILINE)


def match_any(s, regexes):
    return any([match(s, regex) for regex in regexes])


def match_all(s, regexes):
    return all([match(s, regex) for regex in regexes])


def match_pass_regexes(output, regexes):
    if not regexes:
        return
    if not match_all(output, regexes):
        err("Couldn't match test program's output against all of the"\
            " regular expressions:")
        for regex in regexes:
            err(f'\t{regex}')
        sys.exit(1)


def match_fail_regexes(output, regexes):
    if not regexes:
        return
    if match_any(output, regexes):
        err("Matched test program's output against some of the regular"\
            " expressions:")
        for regex in regexes:
            err(f'\t{regex}')
        sys.exit(1)


def run_actual_test_driver(args):
    cmd_line = [args.exe_path] + args.exe_args
    run_func = run
    if args.new_window:
        run_func = run_new_window
    output = run_func(cmd_line)
    if args.new_window and (args.pass_regexes or args.fail_regexes):
        err("Cannot launch child process in a new window and capture its output")
    if output is not None:
        sys.stdout.write(output)
        match_pass_regexes(output, args.pass_regexes)
        match_fail_regexes(output, args.fail_regexes)


def grep_file(args):
    contents = read_file(args.path)
    match_pass_regexes(contents, args.pass_regexes)
    match_fail_regexes(contents, args.fail_regexes)


def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    subparsers = parser.add_subparsers(dest='command')

    parser_run = subparsers.add_parser('run', help='run an executable and check its output')
    parser_run.add_argument('-p', '--pass-regex', nargs='*',
                            dest='pass_regexes', metavar='REGEX',
                            help='pass if all of these regexes match')
    parser_run.add_argument('-f', '--fail-regex', nargs='*',
                            dest='fail_regexes', metavar='REGEX',
                            help='fail if any of these regexes matches')
    parser_run.add_argument('-n', '--new-window', action='store_true',
                            help='launch child process in a new console window')
    parser_run.add_argument('exe_path', metavar='PATH',
                            help='path to the test executable')
    # nargs='*' here would discard additional '--'s.
    parser_run.add_argument('exe_args', metavar='ARG', nargs=argparse.REMAINDER,
                            help='test executable arguments')
    parser_run.set_defaults(func=run_actual_test_driver)

    parser_grep = subparsers.add_parser('grep', help='check file contents for matching patterns')
    parser_grep.add_argument('-p', '--pass-regex', nargs='*',
                             dest='pass_regexes', metavar='REGEX',
                             help='pass if all of these regexes match')
    parser_grep.add_argument('-f', '--fail-regex', nargs='*',
                             dest='fail_regexes', metavar='REGEX',
                             help='fail if any of these regexes matches')
    parser_grep.add_argument('path', metavar='PATH', help='text file path')
    parser_grep.set_defaults(func=grep_file)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.error('please specify a subcommand to run')
    return args


def main(argv=None):
    args = parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
