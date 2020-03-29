# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Build Boost.

This script builds the Boost libraries.  It's main utility is setting the
correct --stagedir parameter value to avoid name clashes.

Usage example:

    $ python -m project.boost.build -- boost_1_71_0/ --with-filesystem --with-program_options
    ...

Consult the output of `python -m project.boost.build --help` for more details.

By default, only builds:

* for the current platform,
* Debug & Release configurations,
* static libraries,
* statically linked to the runtime.
'''

import argparse
from contextlib import contextmanager
import logging
import os.path
import sys
import tempfile

from project.boost.directory import BoostDir
from project.boost.toolchain import Toolchain
from project.configuration import Configuration
from project.linkage import Linkage
from project.platform import Platform
from project.os import on_linux_like
from project.utils import normalize_path, setup_logging


DEFAULT_PLATFORMS = (Platform.native(),)
DEFAULT_CONFIGURATIONS = (Configuration.DEBUG, Configuration.RELEASE,)
DEFAULT_LINK = (Linkage.STATIC,)
DEFAULT_RUNTIME_LINK = Linkage.STATIC
COMMON_B2_ARGS = ['-d0']


class BuildParameters:
    def __init__(self, boost_dir, build_dir=None, platforms=None,
                 configurations=None, link=None, runtime_link=None,
                 mingw=False, b2_args=None):

        boost_dir = normalize_path(boost_dir)
        if build_dir is not None:
            build_dir = normalize_path(build_dir)
        platforms = platforms or DEFAULT_PLATFORMS
        configurations = configurations or DEFAULT_CONFIGURATIONS
        link = link or DEFAULT_LINK
        runtime_link = runtime_link or DEFAULT_RUNTIME_LINK
        if b2_args:
            b2_args = COMMON_B2_ARGS + b2_args
        else:
            b2_args = COMMON_B2_ARGS

        self.boost_dir = boost_dir
        self.build_dir = build_dir
        self.stage_dir = 'stage'
        self.platforms = platforms
        self.configurations = configurations
        self.link = link
        self.runtime_link = runtime_link
        self.mingw = mingw
        self.b2_args = b2_args

    @staticmethod
    def from_args(args):
        return BuildParameters(**vars(args))

    def enum_b2_args(self):
        with self._create_build_dir() as build_dir:
            for platform in self.platforms:
                with Toolchain.detect(platform, mingw=self.mingw) as toolchain:
                    for configuration in self.configurations:
                        for link, runtime_link in self._linkage_options():
                            yield self._build_params(build_dir, toolchain,
                                                     configuration, link,
                                                     runtime_link)

    def _linkage_options(self):
        for link in self.link:
            runtime_link = self.runtime_link
            if runtime_link is Linkage.STATIC:
                if link is Linkage.SHARED:
                    logging.warning("Cannot link the runtime statically to a dynamic library, going to link dynamically")
                    runtime_link = Linkage.SHARED
                elif on_linux_like():
                    logging.warning("Cannot link to the GNU C Library (which is assumed) statically, going to link dynamically")
                    runtime_link = Linkage.SHARED
            yield link, runtime_link

    @contextmanager
    def _create_build_dir(self):
        if self.build_dir is not None:
            logging.info('Build directory: %s', self.build_dir)
            yield self.build_dir
            return

        with tempfile.TemporaryDirectory(dir=os.path.dirname(self.boost_dir)) as build_dir:
            logging.info('Build directory: %s', build_dir)
            try:
                yield build_dir
            finally:
                logging.info('Removing build directory: %s', build_dir)
            return

    def _build_params(self, build_dir, toolchain, configuration, link, runtime_link):
        params = []
        params.append(self._build_dir(build_dir))
        params.append(self._stagedir(toolchain, configuration))
        params += toolchain.get_b2_args()
        params.append(self._link(link))
        params.append(self._runtime_link(runtime_link))
        params.append(self._variant(configuration))
        params += self.b2_args
        return params

    @staticmethod
    def _build_dir(build_dir):
        return f'--build-dir={build_dir}'

    def _stagedir(self, toolchain, configuration):
        # Having different --stagedir values for every configuration/platform
        # combination is unnecessary on Windows.  Even for older Boost versions
        # (when the binaries weren't tagged with their target platform) only a
        # single --stagedir for every platform would suffice.  For newer
        # versions, just a single --stagedir would do, as the binaries are
        # tagged with the target platform, as well as their configuration
        # (a.k.a. "variant" in Boost's terminology).  Still, uniformity helps.
        platform = str(toolchain.platform)
        configuration = str(configuration)
        return f'--stagedir={os.path.join(self.stage_dir, platform, configuration)}'

    @staticmethod
    def _link(link):
        return f'link={link}'

    @staticmethod
    def _runtime_link(runtime_link):
        return f'runtime-link={runtime_link}'

    @staticmethod
    def _variant(configuration):
        return f'variant={configuration.to_boost_variant()}'


def build(params):
    boost_dir = BoostDir(params.boost_dir)
    boost_dir.build(params)


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    logging.info('Command line arguments: %s', argv)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    platform_options = '/'.join(map(str, Platform.all()))
    configuration_options = '/'.join(map(str, Configuration.all()))
    # These are used to put the built libraries into proper stage/
    # subdirectories (to avoid name clashes).
    parser.add_argument('--platform', metavar='PLATFORM', dest='platforms',
                        nargs='*', type=Platform.parse, default=[],
                        help=f'target platform ({platform_options})')
    parser.add_argument('--configuration', metavar='CONFIGURATION', dest='configurations',
                        nargs='*', type=Configuration.parse, default=[],
                        help=f'target configuration ({configuration_options})')

    linkage_options = '/'.join(map(str, Linkage.all()))
    # This is needed because the default behaviour on Linux and Windows is
    # different: static & dynamic libs are built on Linux, but only static libs
    # are built on Windows by default.
    parser.add_argument('--link', metavar='LINKAGE',
                        nargs='*', type=Linkage.parse, default=[],
                        help=f'how the libraries are linked ({linkage_options})')
    # This is used to omit runtime-link=static I'd have to otherwise use a lot,
    # plus the script validates the link= and runtime-link= combinations.
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        type=Linkage.parse, default=DEFAULT_RUNTIME_LINK,
                        help=f'how the libraries link to the runtime ({linkage_options})')

    parser.add_argument('--mingw', action='store_true',
                        help='build using MinGW-w64')

    parser.add_argument('--build', metavar='DIR', dest='build_dir',
                        type=normalize_path,
                        help='Boost build directory (temporary directory unless specified)')
    parser.add_argument('boost_dir', metavar='DIR',
                        type=normalize_path,
                        help='root Boost directory')

    parser.add_argument('b2_args', metavar='B2_ARG',
                        nargs='*', default=[],
                        help='additional b2 arguments, to be passed verbatim')

    return parser.parse_args(argv)


def _main(argv=None):
    with setup_logging():
        build(BuildParameters.from_args(_parse_args(argv)))


if __name__ == '__main__':
    _main()
