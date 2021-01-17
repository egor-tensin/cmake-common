# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import abc
import os.path

from project.boost.version import Version
from project.ci.appveyor.generator import Generator, Image
from project.configuration import Configuration
from project.platform import Platform
from project.utils import env


class Dirs(abc.ABC):
    def __init__(self):
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

    @abc.abstractmethod
    def get_cmake_args(self):
        pass

    def get_boost_help(self):
        return f'''Download & build Boost on Travis/AppVeyor.

This is similar to running both project.boost.download & project.boost.build,
but auto-fills some parameters from environment variables.

Boost is built in {self.get_boost_dir()}.
'''

    def get_cmake_help(self):
        return f'''Build a CMake project on Travis/AppVeyor.

This is similar to running project.cmake.build, but auto-fills some parameters
from environment variables.

The project is built in {self.get_cmake_dir()}.
'''


class Travis(Dirs):
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
