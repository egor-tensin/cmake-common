# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import abc
import os
import os.path

from project.boost.version import Version
from project.ci.appveyor.generator import Generator, Image
from project.configuration import Configuration
from project.platform import Platform
from project.toolchain import ToolchainType
from project.utils import env


class Dirs(abc.ABC):
    @staticmethod
    def detect(hint=None):
        matching = [ci for ci in _ALL_CI_LIST if ci.this_one()]
        if len(matching) == 0:
            raise RuntimeError('no CI system was detected')
        if len(matching) == 1:
            return matching[0]
        # The hint parameter is basically a workaround for when this is run
        # on a CI, _but_ testing another CI is desired.
        if hint is not None:
            for ci in matching:
                if ci.get_name() == hint:
                    return ci
        names = ', '.join(ci.get_name() for ci in matching)
        raise RuntimeError(f"can't select a single CI system out of these: {names}")

    def __init__(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_name():
        pass

    @abc.abstractmethod
    def this_one(self):
        pass

    @staticmethod
    def get_toolset():
        if 'TOOLSET' in os.environ:
            return ToolchainType.parse(os.environ['TOOLSET'])
        return None

    @staticmethod
    def get_platform():
        return Platform.parse(env('PLATFORM'))

    @staticmethod
    def get_configuration():
        return Configuration.parse(env('CONFIGURATION'))

    @abc.abstractmethod
    def get_src_dir(self):
        pass

    def get_build_dir(self):
        return os.path.join(os.path.dirname(self.get_src_dir()), 'build')

    @abc.abstractmethod
    def get_prebuilt_boost_dir(self):
        pass

    @staticmethod
    def get_boost_version():
        return Version.from_string(env('BOOST_VERSION'))

    def get_boost_dir(self):
        return os.path.join(self.get_build_dir(), 'boost')

    def get_cmake_dir(self):
        return os.path.join(self.get_build_dir(), 'cmake')

    def get_install_dir(self):
        return os.path.join(self.get_build_dir(), 'install')

    @abc.abstractmethod
    def get_cmake_args(self):
        pass

    @staticmethod
    def all_ci_names():
        return [ci.get_name() for ci in _ALL_CI_LIST]

    @staticmethod
    def join_ci_names():
        return ', '.join(Dirs.all_ci_names())

    @staticmethod
    def get_boost_help():
        return f'''Download & build Boost during a CI run.

This is similar to running both project.boost.download & project.boost.build,
but auto-fills some parameters from environment variables.

The supported CI systems are: {Dirs.join_ci_names()}.
'''

    @staticmethod
    def get_cmake_help():
        return f'''Build a CMake project during a CI run.

This is similar to running project.cmake.build, but auto-fills some parameters
from environment variables.

The supported CI systems are: {Dirs.join_ci_names()}.
'''


class Travis(Dirs):
    @staticmethod
    def get_name():
        return 'Travis'

    def this_one(self):
        return 'TRAVIS' in os.environ

    def get_src_dir(self):
        return env('TRAVIS_BUILD_DIR')

    def get_prebuilt_boost_dir(self):
        # Travis doesn't have pre-built Boost (available for installation from
        # the official Ubuntu repositories though).
        return None

    def get_cmake_args(self):
        return []


class AppVeyor(Dirs):
    @staticmethod
    def get_name():
        return 'AppVeyor'

    def this_one(self):
        return 'APPVEYOR' in os.environ

    def get_src_dir(self):
        return env('APPVEYOR_BUILD_FOLDER')

    def get_prebuilt_boost_dir(self):
        return Image.get().get_prebuilt_boost_dir()

    def get_cmake_args(self):
        return ['-G', str(Generator.from_image(Image.get()))]


class GitHub(Dirs):
    @staticmethod
    def get_name():
        return 'GitHub Actions'

    def this_one(self):
        return 'GITHUB_ACTIONS' in os.environ

    def get_src_dir(self):
        return env('GITHUB_WORKSPACE')

    def get_prebuilt_boost_dir(self):
        # Used to have 1.72.0 pre-built binaries, but not anymore:
        # https://github.com/actions/virtual-environments/issues/2667
        return None

    def get_cmake_args(self):
        return []


_ALL_CI_LIST = (Travis(), AppVeyor(), GitHub())
