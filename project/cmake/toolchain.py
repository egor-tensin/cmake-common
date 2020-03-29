# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

import abc
from contextlib import contextmanager
import os.path

import project.mingw
from project.platform import Platform
from project.os import on_windows


class Toolchain(abc.ABC):
    @abc.abstractmethod
    def get_cmake_args(self):
        pass

    @staticmethod
    @contextmanager
    def detect(platform, build_dir, mingw=False):
        if mingw:
            with MinGW.setup(platform, build_dir) as toolchain:
                yield toolchain
                return

        if on_windows():
            # MSVC is assumed.
            if platform is None:
                yield Native()
                return
            yield MSVC(platform)
            return

        with GCC.setup(platform, build_dir) as toolchain:
            yield toolchain
            return


class Native(Toolchain):
    def get_cmake_args(self):
        return []


class MSVC(Toolchain):
    def __init__(self, platform):
        self.platform = platform

    def get_cmake_args(self):
        return ['-A', self.platform.get_cmake_arch()]


class File(Toolchain):
    def __init__(self, path):
        self.path = path

    @staticmethod
    def _get_path(build_dir):
        return os.path.join(build_dir, 'custom_toolchain.cmake')

    def get_cmake_args(self):
        return ['-D', f'CMAKE_TOOLCHAIN_FILE={self.path}']


class GCC(File):
    @staticmethod
    def _format(platform):
        return f'''
set(CMAKE_C_COMPILER gcc)
set(CMAKE_C_FLAGS -m{platform.get_address_model()})
set(CMAKE_CXX_COMIPLER g++)
set(CMAKE_CXX_FLAGS -m{platform.get_address_model()})
'''

    @staticmethod
    @contextmanager
    def setup(platform, build_dir):
        if platform is None:
            yield Native()
            return
        path = File._get_path(build_dir)
        with open(path, mode='w') as file:
            file.write(GCC._format(platform))
        yield GCC(path)


class MinGW(File):
    @staticmethod
    def _format(platform):
        return f'''
set(CMAKE_C_COMPILER   {project.mingw.get_gcc(platform)})
set(CMAKE_CXX_COMPILER {project.mingw.get_gxx(platform)})
set(CMAKE_RC_COMILER   {project.mingw.get_windres(platform)})
set(CMAKE_SYSTEM_NAME  Windows)
'''

    @staticmethod
    @contextmanager
    def setup(platform, build_dir):
        platform = platform or Platform.native()
        path = File._get_path(build_dir)
        with open(path, mode='w') as file:
            file.write(MinGW._format(platform))
        yield MinGW(path)
