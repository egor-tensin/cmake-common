# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# Default generator
# -----------------
#
# As of CMake 3.18, the default generator (unless set explicitly) is:
#   * the newest Visual Studio or "NMake Makefiles" on Windows,
#   * "Unix Makefiles" otherwise.
# This is regardless of whether any executables like gcc, cl or make are
# available [1].
#
# Makefile generators
# -------------------
#
# CMake has a number of "... Makefiles" generators.  "Unix Makefiles" uses
# gmake/make/smake, whichever is found first, and cc/c++ for compiler
# detection [2].  "MinGW Makefiles" looks for mingw32-make.exe in a number of
# well-known locations, uses gcc/g++ directly, and is aware of windres [3].  In
# addition, "Unix Makefiles" uses /bin/sh as the SHELL value in the Makefile,
# while the MinGW version uses cmd.exe.  I don't think it matters on Windows
# though, since the non-existent /bin/sh is ignored anyway [4].  "NMake
# Makefiles" is similar, except it defaults to using cl [5].
#
# It's important to _not_ use the -A parameter with any of the Makefile
# generators - it's an error.  This goes for "NMake Makefiles" also.  "NMake
# Makefiles" doesn't attempt to search for installed Visual Studio compilers,
# you need to use it from one of the Visual Studio-provided shells.
#
# Visual Studio generators
# ------------------------
#
# These are special.  They ignore the CMAKE_<LANG>_COMPILER parameters and use
# cl by default [9].  They support specifying the toolset to use via the -T
# parameter (the "Platform Toolset" value in the project's properties) since
# 3.18 [10].  The toolset list varies between Visual Studio versions, and I'm
# too lazy to learn exactly which version supports which toolsets.
#
# cmake --build uses msbuild with Visual Studio generators.  You can pass the
# path to a different cl.exe by doing something like
#
#     msbuild ... /p:CLToolExe=another-cl.exe /p:CLToolPath=C:\parent\dir
#
# It's important that the generators for Visual Studio 2017 or older use Win32
# Win32 as the default platform [12].  Because of that, we need to pass the -A
# parameter.
#
# mingw32-make vs make
# --------------------
#
# No idea what the actual differences are.  The explanation in the FAQ [6]
# about how GNU make "is lacking in some functionality and has modified
# functionality due to the lack of POSIX on Win32" isn't terribly helpful.
#
# It's important that you can install either on Windows (`choco install make`
# for GNU make and `choco install mingw` to install a MinGW-w64 distribution
# with mingw32-make.exe included).  Personally, I don't see any difference
# between using either make.exe or mingw32-make.exe w/ CMake on Windows.  But,
# since MinGW-w64 distributions do include mingw32-make.exe and not make.exe,
# we'll try to detect that.
#
# Cross-compilation
# -----------------
#
# If you want to e.g. build x86 binary on x64 and vice versa, the easiest way
# seems to be to make a CMake "toolchain file", which initializes the proper
# compiler flags (like -m64/-m32, etc.).  Such file could look like this:
#
#     set(CMAKE_C_COMPILER   gcc)
#     set(CMAKE_C_FLAGS      -m32)
#     set(CMAKE_CXX_COMPILER g++)
#     set(CMAKE_CXX_FLAGS    -m32)
#
# You can then pass the path to it using the CMAKE_TOOLCHAIN_FILE parameter.
#
# If you use the Visual Studio generators, just use the -A parameter, like "-A
# Win32".
#
# As a side note, if you want to cross-compile between x86 and x64 using GCC on
# Ubuntu, you need to install the gcc-multilib package.
#
# Windows & Clang
# ---------------
#
# Using Clang on Windows is no easy task, of course.  Prior to 3.15, there was
# no support for building things using the clang++.exe executable, only
# clang-cl.exe was supported [7].  If you specified -DCMAKE_CXX_COMPILER=clang++,
# CMake would stil pass MSVC-style command line options to the compiler (like
# /MD, /nologo, etc.), which clang++ doesn't like [8].
#
# So, in summary, you can only use clang++ since 3.15.  clang-cl doesn't work
# with Visual Studio generators unless you specify the proper toolset using the
# -T parameter.  You can set the ClToolExe property using msbuild, but while
# that might work in practice, clang-cl.exe needs to map some unsupported
# options for everything to work properly.  For an example of how this is done,
# see the LLVM.Cpp.Common.* files at [11].
#
# I recommend using Clang (either clang-cl or clang++ since 3.15) using the
# "NMake Makefiles" generator.
#
# References
# ----------
#
# [1]: cmake::EvaluateDefaultGlobalGenerator
#      https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmake.cxx
# [2]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmGlobalUnixMakefileGenerator3.cxx
# [3]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmGlobalMinGWMakefileGenerator.cxx
# [4]: https://www.gnu.org/software/make/manual/html_node/Choosing-the-Shell.html
# [5]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmGlobalNMakeMakefileGenerator.cxx
# [6]: http://mingw.org/wiki/FAQ
# [7]: https://cmake.org/cmake/help/v3.15/release/3.15.html#compilers
# [8]: https://github.com/Kitware/CMake/blob/v3.14.7/Modules/Platform/Windows-Clang.cmake
# [9]: https://gitlab.kitware.com/cmake/cmake/-/issues/19174
# [10]: https://cmake.org/cmake/help/v3.8/release/3.8.html
# [11]: https://github.com/llvm/llvm-project/tree/e408935bb5339e20035d84307c666fbdd15e99e0/llvm/tools/msbuild
# [12]: https://cmake.org/cmake/help/v3.18/generator/Visual%20Studio%2015%202017.html

import abc
import os.path
import shutil

import project.mingw
from project.os import on_windows
from project.platform import Platform
from project.toolchain import ToolchainType


class Toolchain(abc.ABC):
    @abc.abstractmethod
    def get_cmake_args(self):
        pass

    @abc.abstractmethod
    def get_build_args(self):
        pass

    @staticmethod
    def detect(hint, platform, build_dir):
        if hint is ToolchainType.AUTO:
            # If the platform wasn't specified, auto-detect everything.
            # There's no need to set -mXX flags, etc.
            if platform is None:
                return Auto()
            # If a specific platform was requested, we might need to set some
            # CMake/compiler flags.
            if on_windows():
                # We need to specify the -A parameter.  This might break if
                # none of the Visual Studio generators are available, but the
                # NMake one is, although I don't know how this can be possible
                # normally.
                hint = ToolchainType.MSVC
            else:
                # Same thing for the -m32/-m64 flags.
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
    def get_cmake_args(self):
        return []

    def get_build_args(self):
        return []


class MSVC(Auto):
    def __init__(self, platform):
        self.platform = platform

    def get_cmake_args(self):
        if self.platform is None:
            return []
        # This doesn't actually specify the generator of course, but I don't
        # want to implement VS detection logic.
        return ['-A', self.platform.get_cmake_arch()]

    def get_build_args(self):
        return ['/m']


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

    @staticmethod
    def _format_platform_compiler_flags(platform):
        if platform is None:
            # If the platform wasn't specified, don't use the -m flag, etc.
            return ''
        # Otherwise, use the standard -m32/-m64 flags.
        return f'''
set(CMAKE_C_FLAGS   -m{platform.get_address_model()})
set(CMAKE_CXX_FLAGS -m{platform.get_address_model()})
'''

    def get_cmake_args(self):
        return [
            '-D', f'CMAKE_TOOLCHAIN_FILE={self.path}',
            # The Visual Studio generator is the default on Windows, override
            # it:
            '-G', self._get_makefile_generator(),
        ]

    def get_build_args(self):
        return []


class GCC(Makefile):
    @staticmethod
    def _format(platform):
        return f'''
set(CMAKE_C_COMPILER   gcc)
set(CMAKE_CXX_COMPILER g++)
{Makefile._format_platform_compiler_flags(platform)}'''

    @staticmethod
    def setup(platform, build_dir):
        return GCC.write_config(build_dir, GCC._format(platform))


class MinGW(Makefile):
    @staticmethod
    def _format(platform):
        if platform is None:
            # MinGW only supports x86/x64, plus we need the platform for the
            # compiler file name, so default to x64 unless specified.
            platform = Platform.X64
        return f'''
set(CMAKE_C_COMPILER   {project.mingw.get_gcc(platform)})
set(CMAKE_CXX_COMPILER {project.mingw.get_gxx(platform)})
set(CMAKE_AR           {project.mingw.get_ar(platform)})
set(CMAKE_RANLIB       {project.mingw.get_ranlib(platform)})
set(CMAKE_RC_COMPILER  {project.mingw.get_windres(platform)})
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
{Makefile._format_platform_compiler_flags(platform)}'''

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
{Makefile._format_platform_compiler_flags(platform)}'''

    @staticmethod
    def setup(platform, build_dir):
        return ClangCL.write_config(build_dir, ClangCL._format(platform))
