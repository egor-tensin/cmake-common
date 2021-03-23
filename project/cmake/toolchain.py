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
from project.toolchain import ToolchainType


class Toolchain(abc.ABC):
    @abc.abstractmethod
    def cmake_args(self):
        pass

    @abc.abstractmethod
    def build_system_args(self):
        pass

    @staticmethod
    def detect(hint, platform, build_dir):
        if hint is ToolchainType.AUTO:
            if on_windows():
                # On Windows, 'auto' means 'msvc', and we need to specify the
                # -A parameter.  This might break if none of the Visual Studio
                # generators are available, but the NMake one is, although I
                # don't know how this can be possible normally.
                hint = ToolchainType.MSVC
            else:
                # On Linux, if the platform wasn't specified, auto-detect
                # everything.  There's no need to set -mXX flags, etc.
                if platform is Platform.AUTO:
                    return Auto()
                # If a specific platform was requested, we might need to set
                # some CMake/compiler flags, like -m32/-m64.
                hint = ToolchainType.GCC
        if hint is ToolchainType.MSVC:
            return MSVC(platform)
        if hint is ToolchainType.GCC:
            return GCC.setup(platform, build_dir)
        if hint is ToolchainType.MINGW:
            return MinGW.setup(platform, build_dir)
        if hint is ToolchainType.CLANG:
            return Clang.setup(platform, build_dir)
        if hint is ToolchainType.CLANG_CL:
            return ClangCL.setup(platform, build_dir)
        raise NotImplementedError(f'unrecognized toolset: {hint}')


class Auto(Toolchain):
    def cmake_args(self):
        return []

    def build_system_args(self):
        return []


class MSVC(Auto):
    def __init__(self, platform):
        self.platform = platform

    def cmake_args(self):
        # This doesn't actually specify the generator of course, but I don't
        # want to implement VS detection logic.
        return ['-A', self.platform.msvc_arch()]

    def build_system_args(self):
        return []


class Makefile(Toolchain):
    def __init__(self, path):
        self.path = path

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

    @classmethod
    def write_config(cls, build_dir, contents):
        path = Makefile._get_config_path(build_dir)
        with open(path, mode='w') as file:
            file.write(contents)
        return cls(path)

    def cmake_args(self):
        return [
            '-D', f'CMAKE_TOOLCHAIN_FILE={self.path}',
            # The Visual Studio generator is the default on Windows, override
            # it:
            '-G', self._get_makefile_generator(),
        ]

    def build_system_args(self):
        return []


class GCC(Makefile):
    @staticmethod
    def _format(platform):
        return f'''
set(CMAKE_C_COMPILER   gcc)
set(CMAKE_CXX_COMPILER g++)
{platform.makefile_toolchain_file()}'''

    @staticmethod
    def setup(platform, build_dir):
        return GCC.write_config(build_dir, GCC._format(platform))


class MinGW(Makefile):
    @staticmethod
    def _format(platform):
        paths = project.mingw.MinGW(platform)
        return f'''
set(CMAKE_C_COMPILER   {paths.gcc()})
set(CMAKE_CXX_COMPILER {paths.gxx()})
set(CMAKE_AR           {paths.ar()})
set(CMAKE_RANLIB       {paths.ranlib()})
set(CMAKE_RC_COMPILER  {paths.windres()})
set(CMAKE_SYSTEM_NAME  Windows)
'''

    @staticmethod
    def setup(platform, build_dir):
        return MinGW.write_config(build_dir, MinGW._format(platform))


class Clang(Makefile):
    @staticmethod
    def _format(platform):
        return f'''
if(CMAKE_VERSION VERSION_LESS "3.15" AND WIN32)
    set(CMAKE_C_COMPILER   clang-cl)
    set(CMAKE_CXX_COMPILER clang-cl)
else()
    set(CMAKE_C_COMPILER   clang)
    set(CMAKE_CXX_COMPILER clang++)
endif()
{platform.makefile_toolchain_file()}'''

    def _get_makefile_generator(self):
        if on_windows():
            # MinGW utilities like make might be unavailable, but NMake can
            # very much be there.
            if shutil.which('nmake'):
                return 'NMake Makefiles'
        return super()._get_makefile_generator()

    @staticmethod
    def setup(platform, build_dir):
        return Clang.write_config(build_dir, Clang._format(platform))


class ClangCL(Clang):
    @staticmethod
    def _format(platform):
        return f'''
set(CMAKE_C_COMPILER   clang-cl)
set(CMAKE_CXX_COMPILER clang-cl)
set(CMAKE_SYSTEM_NAME  Windows)
{platform.makefile_toolchain_file()}'''

    @staticmethod
    def setup(platform, build_dir):
        return ClangCL.write_config(build_dir, ClangCL._format(platform))
