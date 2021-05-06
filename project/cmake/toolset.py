# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# See docs/cmake.md for a more thorough description of my pain.

import abc
import os.path
import shutil

import project.mingw
from project.os import on_windows
from project.platform import Platform
from project.toolset import ToolsetHint


class Toolset(abc.ABC):
    def cmake_args(self, build_dir, platform):
        return []

    def build_system_args(self):
        return []

    @staticmethod
    def detect(hint):
        if hint is ToolsetHint.AUTO:
            return Auto
        if hint is ToolsetHint.MSVC:
            return MSVC
        if hint is ToolsetHint.GCC:
            return GCC
        if hint is ToolsetHint.MINGW:
            return MinGW
        if hint is ToolsetHint.CLANG:
            return Clang
        if hint is ToolsetHint.CLANG_CL:
            return ClangCL
        raise NotImplementedError(f'unrecognized toolset: {hint}')

    @staticmethod
    def make(hint, platform):
        cls = Toolset.detect(hint)
        if cls is MinGW:
            return MinGW(platform)
        return cls()


class Auto(Toolset):
    def cmake_args(self, build_dir, platform):
        if on_windows():
            # On Windows, 'auto' means 'msvc', and we need to specify the -A
            # parameter.  This might break if none of the Visual Studio
            # generators are available, but the NMake one is, although I don't
            # know how this can be possible normally.
            return MSVC().cmake_args(build_dir, platform)
        # On Linux, if the platform wasn't specified, auto-detect everything.
        # There's no need to set -mXX flags, etc.
        if platform is Platform.AUTO:
            return []
        # If a specific platform was requested, we might need to set some
        # CMake/compiler flags, like -m32/-m64.
        return GCC().cmake_args(build_dir, platform)


class MSVC(Auto):
    def cmake_args(self, build_dir, platform):
        # This doesn't actually specify the generator of course, but I don't
        # want to implement VS detection logic.
        return ['-A', platform.msvc_arch()]


class Makefile(Toolset):
    @staticmethod
    def _get_config_path(build_dir):
        return os.path.join(build_dir, 'custom_toolchain.cmake')

    @staticmethod
    def _get_makefile_generator():
        if on_windows():
            if shutil.which('mingw32-make'):
                return 'MinGW Makefiles'
            return 'Unix Makefiles'
        # On Linux/Cygwin, make all the way:
        return 'Unix Makefiles'

    @staticmethod
    def _write_config(build_dir, contents):
        path = Makefile._get_config_path(build_dir)
        with open(path, mode='w') as file:
            file.write(contents)
        return path

    @abc.abstractmethod
    def format_cmake_toolset_file(self, platform):
        pass

    def cmake_args(self, build_dir, platform):
        contents = self.format_cmake_toolset_file(platform)
        config_path = self._write_config(build_dir, contents)
        return [
            '-D', f'CMAKE_TOOLCHAIN_FILE={config_path}',
            # The Visual Studio generator is the default on Windows, override
            # it:
            '-G', self._get_makefile_generator(),
        ]


class GCC(Makefile):
    def format_cmake_toolset_file(self, platform):
        return f'''
set(CMAKE_C_COMPILER   gcc)
set(CMAKE_CXX_COMPILER g++)
{platform.makefile_toolset_file()}'''


class MinGW(Makefile):
    def __init__(self, platform):
        self.paths = project.mingw.MinGW(platform)

    def format_cmake_toolset_file(self, platform):
        return f'''
set(CMAKE_C_COMPILER   {self.paths.gcc()})
set(CMAKE_CXX_COMPILER {self.paths.gxx()})
set(CMAKE_AR           {self.paths.ar()})
set(CMAKE_RANLIB       {self.paths.ranlib()})
set(CMAKE_RC_COMPILER  {self.paths.windres()})
set(CMAKE_SYSTEM_NAME  Windows)
'''


class Clang(Makefile):
    def format_cmake_toolset_file(self, platform):
        return f'''
if(CMAKE_VERSION VERSION_LESS "3.15" AND WIN32)
    set(CMAKE_C_COMPILER   clang-cl)
    set(CMAKE_CXX_COMPILER clang-cl)
else()
    set(CMAKE_C_COMPILER   clang)
    set(CMAKE_CXX_COMPILER clang++)
endif()
{platform.makefile_toolset_file()}'''

    def _get_makefile_generator(self):
        if on_windows():
            # MinGW utilities like make might be unavailable, but NMake can
            # very much be there.
            if shutil.which('nmake'):
                return 'NMake Makefiles'
        return super()._get_makefile_generator()


class ClangCL(Clang):
    def format_cmake_toolset_file(self, platform):
        return f'''
set(CMAKE_C_COMPILER   clang-cl)
set(CMAKE_CXX_COMPILER clang-cl)
set(CMAKE_SYSTEM_NAME  Windows)
{platform.makefile_toolset_file()}'''
