# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

R'''Build Boost.

The main utility of this script is setting the correct --prefix parameter value
to avoid name clashes.

It also facilitates building with different toolsets/for different platforms
with the help from the --toolset and --platform parameters.

Usage example:

    $ boost-build boost_1_71_0/ filesystem program_options
    ...

Consult the output of `boost-build --help` for more details.

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
from project.configuration import Configuration
from project.linkage import Linkage
from project.platform import Platform
from project.toolset import Toolset, ToolsetVersion
from project.utils import normalize_path, setup_logging
import project.version


DEFAULT_PLATFORMS = (Platform.AUTO,)
DEFAULT_CONFIGURATIONS = (Configuration.DEBUG, Configuration.RELEASE,)
DEFAULT_TOOLSET_VERSION = ToolsetVersion.default()
B2_QUIET = ['warnings=off', '-d0']
B2_VERBOSE = ['warnings=all', '-d2', '--debug-configuration']


class BuildParameters:
    def __init__(self, boost_dir, libraries, build_dir=None, platforms=None,
                 configurations=None, link=None, runtime_link=None,
                 toolset_version=None, verbose=False, b2_args=None):

        boost_dir = normalize_path(boost_dir)
        libraries = libraries or []
        if build_dir is not None:
            build_dir = normalize_path(build_dir)
        platforms = platforms or DEFAULT_PLATFORMS
        configurations = configurations or DEFAULT_CONFIGURATIONS
        link = link or Linkage.default_link()
        runtime_link = runtime_link or Linkage.default_runtime_link()
        toolset_version = toolset_version or DEFAULT_TOOLSET_VERSION
        verbosity = B2_VERBOSE if verbose else B2_QUIET
        if b2_args:
            b2_args = verbosity + b2_args
        else:
            b2_args = verbosity

        self.boost_dir = boost_dir
        self.libraries = libraries
        self.build_dir = build_dir
        self.platforms = platforms
        self.configurations = configurations
        self.link = link
        self.runtime_link = runtime_link
        self.toolset_version = toolset_version
        self.b2_args = b2_args

    @staticmethod
    def from_cmd_args(args):
        args = vars(args)
        args.pop('help_toolsets', None)
        return BuildParameters(**args)

    def enum_b2_args(self):
        with self._create_build_dir() as build_dir:
            for platform in self.platforms:
                for configuration in self.configurations:
                    with self._b2_args(build_dir, platform, configuration) as args:
                        yield args

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

    @contextmanager
    def _b2_args(self, build_dir, platform, configuration):
        toolset = Toolset.make(self.toolset_version, platform)
        link, runtime_link = Linkage.validate_linkage(self.link, self.runtime_link)
        with toolset.b2_args() as result:
            result.append(f'--build-dir={build_dir}')
            result.append('--layout=system')
            result += platform.b2_args(configuration)
            result += configuration.b2_args()
            result += link.b2_args_link()
            result += runtime_link.b2_args_runtime_link()
            result += self.b2_args
            if self.libraries:
                result += [f'--with-{lib}' for lib in self.libraries]
            result += ['install']
            yield result


def build(params):
    boost_dir = BoostDir(params.boost_dir)
    boost_dir.build(params)


def _parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if '--help-toolsets' in argv:
        sys.stdout.write(ToolsetVersion.help_toolsets())
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--help-toolsets', action='store_true',
                        help='show detailed info about supported toolsets')

    project.version.add_to_arg_parser(parser)

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose b2 invocation (quiet by default)')

    parser.add_argument('--toolset', metavar='TOOLSET', dest='toolset_version',
                        type=ToolsetVersion.parse, default=DEFAULT_TOOLSET_VERSION,
                        help=f'toolset to use ({ToolsetVersion.usage()})')

    platform_options = '/'.join(map(str, Platform.all()))
    configuration_options = '/'.join(map(str, Configuration.all()))
    # These are used to put the built libraries into proper installation
    # directory subdirectories (to avoid name clashes).
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
                        type=Linkage.parse, default=Linkage.default_link(),
                        help=f'how the libraries are linked ({linkage_options})')
    # This is used to omit runtime-link=static I'd have to otherwise use a lot,
    # plus the script validates the link= and runtime-link= combinations.
    parser.add_argument('--runtime-link', metavar='LINKAGE',
                        type=Linkage.parse, default=Linkage.default_runtime_link(),
                        help=f'how the libraries link to the runtime ({linkage_options})')

    parser.add_argument('--build', metavar='DIR', dest='build_dir',
                        type=normalize_path,
                        help='Boost build directory (temporary directory unless specified)')

    parser.add_argument('--b2-arg', metavar='ARG', dest='b2_args',
                        action='extend', nargs='*',
                        help='additional b2 arguments, to be passed verbatim')

    parser.add_argument('boost_dir', metavar='BOOST_DIR',
                        type=normalize_path,
                        help='root Boost directory')
    parser.add_argument('libraries', metavar='LIBRARIES',
                        action='extend', nargs='*',
                        help='libraries to build (all libraries by default)')

    return parser.parse_args(argv)


def _main(argv=None):
    args = _parse_args(argv)
    with setup_logging():
        build(BuildParameters.from_cmd_args(args))


if __name__ == '__main__':
    _main()
