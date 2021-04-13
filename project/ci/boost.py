# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import argparse
import sys

from project.boost.build import BuildParameters, build
from project.boost.download import DownloadParameters, download
from project.ci.dirs import Dirs
from project.linkage import Linkage
from project.utils import setup_logging


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=Dirs.get_boost_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--link', metavar='LINKAGE',
                        nargs='*', type=Linkage.parse,
                        help='how the libraries are linked')
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        type=Linkage.parse,
                        help='how the libraries link to the runtime')

    # The hint parameter is basically a workaround for when this is run on a
    # CI, _but_ testing another CI is desired.  This shouldn't be used in a
    # real CI workflow.
    parser.add_argument('--hint', metavar='CI_NAME',
                        choices=Dirs.all_ci_names(),
                        help=argparse.SUPPRESS)

    parser.add_argument('b2_args', metavar='B2_ARG',
                        nargs='*', default=[],
                        help='additional b2 arguments, to be passed verbatim')

    return parser.parse_args(argv)


def build_ci(dirs, argv=None):
    args = _parse_args(argv)
    with setup_logging():
        if dirs is None:
            dirs = Dirs.detect(args.hint)

        version = dirs.get_boost_version()
        build_dir = dirs.get_build_dir()
        boost_dir = dirs.get_boost_dir()
        params = DownloadParameters(version, cache_dir=build_dir, dest_path=boost_dir)
        download(params)

        params = BuildParameters(boost_dir,
                                 platforms=(dirs.get_platform(),),
                                 configurations=(dirs.get_configuration(),),
                                 link=args.link,
                                 runtime_link=args.runtime_link,
                                 toolset=dirs.get_toolset(),
                                 b2_args=args.b2_args)
        build(params)


def main(argv=None):
    build_ci(None, argv)


if __name__ == '__main__':
    main()
