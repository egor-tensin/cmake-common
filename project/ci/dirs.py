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
from project.utils import env


class Dirs(abc.ABC):
    @staticmethod
    def detect():
        matching = [ci for ci in _ALL_CI_LIST if ci.this_one()]
        if len(matching) == 0:
            raise RuntimeError('no CI system was detected')
        if len(matching) > 1:
            names = ', '.join(ci.get_name() for ci in matching)
            raise RuntimeError(f"can't select a single CI system out of these: {names}")
        return matching[0]

    def __init__(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def get_name():
        pass

    @abc.abstractmethod
    def this_one(self):
        pass

    @abc.abstractmethod
    def get_platform(self):
        pass

    @abc.abstractmethod
    def get_configuration(self):
        pass

    @abc.abstractmethod
    def get_src_dir(self):
        pass

    @abc.abstractmethod
    def get_build_dir(self):
        pass

    def get_boost_version(self):
        return Version.from_string(env('boost_version'))

    def get_boost_dir(self):
        return os.path.join(self.get_build_dir(), 'boost')

    def get_cmake_dir(self):
        return os.path.join(self.get_build_dir(), 'build')

    def get_install_dir(self):
        return os.path.join(self.get_build_dir(), 'install')

    @abc.abstractmethod
    def get_cmake_args(self):
        pass

    @staticmethod
    def get_boost_help():
        names = ', '.join(ci.get_name() for ci in _ALL_CI_LIST)
        return f'''Download & build Boost during a CI run.

This is similar to running both project.boost.download & project.boost.build,
but auto-fills some parameters from environment variables.

The supported CI systems are: {names}.
'''

    @staticmethod
    def get_cmake_help():
        names = ', '.join(ci.get_name() for ci in _ALL_CI_LIST)
        return f'''Build a CMake project during a CI run.

This is similar to running project.cmake.build, but auto-fills some parameters
from environment variables.

The supported CI systems are: {names}.
'''


class Travis(Dirs):
    @staticmethod
    def get_name():
        return 'Travis'

    def this_one(self):
        return 'TRAVIS' in os.environ

    def get_platform(self):
        return Platform.parse(env('platform'))

    def get_configuration(self):
        return Configuration.parse(env('configuration'))

    def get_src_dir(self):
        return env('TRAVIS_BUILD_DIR')

    def get_build_dir(self):
        return env('HOME')

    def get_cmake_args(self):
        return []


class AppVeyor(Dirs):
    @staticmethod
    def get_name():
        return 'AppVeyor'

    def this_one(self):
        return 'APPVEYOR' in os.environ

    def get_platform(self):
        return Platform.parse(env('PLATFORM'))

    def get_configuration(self):
        return Configuration.parse(env('CONFIGURATION'))

    def get_src_dir(self):
        return env('APPVEYOR_BUILD_FOLDER')

    def get_build_dir(self):
        return R'C:\projects'

    def get_cmake_args(self):
        return ['-G', str(Generator.from_image(Image.get()))]


class GitHub(Dirs):
    @staticmethod
    def get_name():
        return 'GitHub Actions'

    def this_one(self):
        return 'GITHUB_ACTIONS' in os.environ

    def get_platform(self):
        return Platform.parse(env('platform'))

    def get_configuration(self):
        return Configuration.parse(env('configuration'))

    def get_src_dir(self):
        return env('GITHUB_WORKSPACE')

    def get_build_dir(self):
        return os.path.dirname(env('GITHUB_WORKSPACE'))

    def get_cmake_args(self):
        return []


_ALL_CI_LIST = (Travis(), AppVeyor(), GitHub())
