# Copyright (c) 2021 Egor Tensin <egor@tensin.name>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common
# Distributed under the MIT License.

"""Wrap your actual test driver to use with CTest

CTest suffers from at least two issues, in particular with regard to its
PASS_REGULAR_EXPRESSION feature:

1. The regular expression syntax used by CMake is deficient.
2. The exit code of a test is ignored if one of the regexes matches.

This script tries to fix them.
"""

import argparse
import logging
import re
import subprocess
import sys

from project import utils
import project.version


def _run_is_valid_code(actual, expected):
    if actual in expected:
        return True
    logging.error(
        "Actual exit code %d is not among the allowed codes %s", actual, str(expected)
    )
    return False


def run(cmd_line, exit_codes=(0,)):
    try:
        return utils.run_capture(cmd_line)
    except subprocess.CalledProcessError as e:
        if not _run_is_valid_code(e.returncode, exit_codes):
            raise
        return e.stdout


def run_new_window(cmd_line, exit_codes=(0,)):
    try:
        utils.run(cmd_line, creationflags=subprocess.CREATE_NEW_CONSOLE)
    except subprocess.CalledProcessError as e:
        if not _run_is_valid_code(e.returncode, exit_codes):
            raise


def match(s, regex):
    return re.search(regex, s, flags=re.MULTILINE)


def match_pass_regexes(output, regexes):
    if not regexes:
        return True
    for regex in regexes:
        if match(output, regex):
            continue
        logging.error(
            r"""Couldn't match test program's output against "pass" regex: %s""", regex
        )
        return False
    return True


def match_fail_regexes(output, regexes):
    if not regexes:
        return False
    for regex in regexes:
        if not match(output, regex):
            continue
        logging.error(
            r"""Matched test program's output against "fail" regex: %s""", regex
        )
        return True
    return False


def _match_output(output, pass_regexes, fail_regexes):
    if not match_pass_regexes(output, pass_regexes):
        return 1
    if match_fail_regexes(output, fail_regexes):
        return 1
    return 0


def action_run(args):
    cmd_line = [args.exe_path] + args.exe_args
    run_func = run
    if args.new_window:
        run_func = run_new_window
    output = run_func(cmd_line, args.exit_codes)
    if args.new_window and (args.pass_regexes or args.fail_regexes):
        logging.error(
            "Cannot launch child process in a new window and capture its output"
        )
    if output is None:
        return 0
    return _match_output(output, args.pass_regexes, args.fail_regexes)


def action_grep(args):
    contents = utils.read_file(args.path)
    return _match_output(contents, args.pass_regexes, args.fail_regexes)


def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    project.version.add_to_arg_parser(parser)

    subparsers = parser.add_subparsers(dest="command")

    parser_run = subparsers.add_parser(
        "run", help="run an executable and check its output"
    )
    parser_run.add_argument(
        "-p",
        "--pass-regex",
        nargs="*",
        dest="pass_regexes",
        metavar="REGEX",
        help="pass if all of these regexes match",
    )
    parser_run.add_argument(
        "-f",
        "--fail-regex",
        nargs="*",
        dest="fail_regexes",
        metavar="REGEX",
        help="fail if any of these regexes matches",
    )
    parser_run.add_argument(
        "-e",
        "--exit-code",
        nargs="*",
        type=int,
        default=[0],
        dest="exit_codes",
        metavar="NUM",
        help="allowed exit_codes (only 0 by default)",
    )
    parser_run.add_argument(
        "-n",
        "--new-window",
        action="store_true",
        help="launch child process in a new console window",
    )
    parser_run.add_argument(
        "exe_path",
        metavar="PATH",
        help="path to the test executable",
    )
    # nargs='*' here would discard additional '--'s.
    parser_run.add_argument(
        "exe_args",
        metavar="ARG",
        nargs=argparse.REMAINDER,
        help="test executable arguments",
    )
    parser_run.set_defaults(func=action_run)

    parser_grep = subparsers.add_parser(
        "grep", help="check file contents for matching patterns"
    )
    parser_grep.add_argument(
        "-p",
        "--pass-regex",
        nargs="*",
        dest="pass_regexes",
        metavar="REGEX",
        help="pass if all of these regexes match",
    )
    parser_grep.add_argument(
        "-f",
        "--fail-regex",
        nargs="*",
        dest="fail_regexes",
        metavar="REGEX",
        help="fail if any of these regexes matches",
    )
    parser_grep.add_argument(
        "path",
        metavar="PATH",
        help="text file path",
    )
    parser_grep.set_defaults(func=action_grep)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("please specify a subcommand to run")
    return args


def main(argv=None):
    args = parse_args(argv)
    with utils.setup_logging(verbose=True):
        return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
