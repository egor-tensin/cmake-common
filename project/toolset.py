# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''Supported platform/build system/compiler combinations include, but are not
limited to:

| Platform | Build system | Compiler
| -------- | ------------ | --------
| Linux    | make         | Clang
|          |              | GCC
|          |              | MinGW-w64
| Windows  | make [1]     | Clang (clang/clang++)
|          |              | Clang (clang-cl [2])
|          |              | MinGW-w64
|          | msbuild      | MSVC
| Cygwin   | make         | Clang
|          |              | GCC
|          |              | MinGW-w64

1. Both GNU make and MinGW mingw32-make.
2. Boost 1.69.0 or higher only.
'''

# See docs/{boost,cmake}.md for a more thorough description of my pain.

import abc
import argparse
from contextlib import contextmanager
from enum import Enum
import logging
import os.path
import shutil

import project.mingw
from project.os import on_cygwin, on_linux, on_windows
from project.platform import Platform
from project.utils import temp_file


class ToolsetHint(Enum):
    AUTO = 'auto'   # This most commonly means GCC on Linux and MSVC on Windows.
    MSVC = 'msvc'   # Force MSVC.
    GCC = 'gcc'     # Force GCC.
    MINGW = 'mingw' # As in MinGW-w64; GCC with the PLATFORM-w64-mingw32 prefix.
    CLANG = 'clang'
    CLANG_CL = 'clang-cl'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def all():
        return tuple(ToolsetHint)

    @staticmethod
    def parse(s):
        try:
            return ToolsetHint(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid toolset: {s}') from e


class Toolset(abc.ABC):
    @contextmanager
    def b2_args(self):
        # Write the config file, etc.
        yield []

    @staticmethod
    def bootstrap_bat_args():
        return []

    @staticmethod
    def bootstrap_sh_args():
        return []

    @staticmethod
    def cmake_args(build_dir, platform):
        return []

    @staticmethod
    def build_system_args():
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
        # Platform is required here, since some toolsets (MinGW-w64) require
        # it for the compiler path.
        cls = Toolset.detect(hint)
        if cls is MinGW:
            return MinGW(platform)
        return cls()


class Auto(Toolset):
    # Let Boost.Build do the detection.  Most commonly it means GCC on
    # Linux-likes and MSVC on Windows.

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


class MSVC(Toolset):
    @contextmanager
    def b2_args(self):
        yield ['toolset=msvc']

    # Note: bootstrap.bat picks up MSVC by default.

    def cmake_args(self, build_dir, platform):
        # This doesn't actually specify the generator of course, but I don't
        # want to implement VS detection logic.
        return ['-A', platform.msvc_arch()]


def _full_exe_name(exe):
    if on_linux():
        # There's no PATHEXT on Linux.
        return exe
    # b2 on Windows/Cygwin doesn't like it when the executable name doesn't
    # include the extension.
    dir_path = os.path.dirname(exe) or None
    path = shutil.which(exe, path=dir_path)
    if not path:
        raise RuntimeError(f"executable '{exe}' could not be found")
    if on_cygwin():
        # On Cygwin, shutil.which('gcc') == '/usr/bin/gcc' and shutil.which('gcc.exe')
        # == '/usr/bin/gcc.exe'; we want the latter version.  shutil.which('clang++')
        # == '/usr/bin/clang++' is fine though, since it _is_ the complete path
        # (clang++ is a symlink).
        if os.path.exists(path) and os.path.exists(path + '.exe'):
            path += '.exe'
    if dir_path:
        # If it was found in a specific directory, include the directory in the
        # result.  shutil.which returns the executable name prefixed with the
        # path argument.
        return path
    # If it was found in PATH, just return the basename (which includes the
    # extension).
    return os.path.basename(path)


class BoostCustom(Toolset):
    COMPILER_VERSION = 'custom'

    def __init__(self, compiler, path=None, build_options=None):
        if not compiler:
            raise RuntimeError('compiler type is required (like gcc, clang, etc.)')
        self.compiler = compiler
        version = BoostCustom.COMPILER_VERSION
        self.version = version
        path = path or ''
        path = path and _full_exe_name(path)
        self.path = path
        build_options = build_options or []
        self.build_options = build_options

    def b2_toolset(self):
        if self.version:
            return f'{self.compiler}-{self.version}'
        return self.compiler

    def b2_toolset_arg(self):
        return f'toolset={self.b2_toolset()}'

    @contextmanager
    def _b2_write_config(self):
        config_file = temp_file(prefix='user_config_', suffix='.jam')
        with config_file as config_path:
            config = self.b2_format_config()
            logging.info('Using user config:\n%s', config)
            with open(config_path, mode='w') as fd:
                fd.write(config)
            yield config_path

    def _b2_format_build_options(self):
        return ''.join(f'\n    <{name}>{val}' for name, val in self.build_options)

    def b2_format_config(self):
        version = self.version and f'{self.version} '
        path = self.path and f'{self.path} '
        return f'''using {self.compiler} : {version}: {path}:{self._b2_format_build_options()}
;'''

    @contextmanager
    def b2_args(self):
        with self._b2_write_config() as config_path:
            args = []
            args.append(self.b2_toolset_arg())
            args.append(f'--user-config={config_path}')
            yield args


class CMakeCustom(Toolset):
    @staticmethod
    def cmake_generator():
        return CMakeCustom.makefiles()

    @staticmethod
    def makefiles():
        if on_windows():
            if shutil.which('mingw32-make'):
                return 'MinGW Makefiles'
            return 'Unix Makefiles'
        # On Linux/Cygwin, make all the way:
        return 'Unix Makefiles'

    @staticmethod
    def nmake_or_makefiles():
        if on_windows():
            # MinGW utilities like make might be unavailable, but NMake can
            # very much be there.
            if shutil.which('nmake'):
                return 'NMake Makefiles'
        return CMakeCustom.cmake_generator()

    @staticmethod
    def _cmake_write_config(build_dir, contents):
        path = os.path.join(build_dir, 'custom_toolchain.cmake')
        with open(path, mode='w') as file:
            file.write(contents)
        return path

    @abc.abstractmethod
    def cmake_format_config(self, platform):
        pass

    def cmake_args(self, build_dir, platform):
        contents = self.cmake_format_config(platform)
        config_path = self._cmake_write_config(build_dir, contents)
        return [
            '-D', f'CMAKE_TOOLCHAIN_FILE={config_path}',
            # The Visual Studio generator is the default on Windows, override
            # it:
            '-G', self.cmake_generator(),
        ]


class GCC(BoostCustom, CMakeCustom):
    # Force GCC.  We don't care whether it's a native Linux GCC or a
    # MinGW-flavoured GCC on Windows.

    def __init__(self):
        BoostCustom.__init__(self, 'gcc', 'g++', self.b2_build_options())
        CMakeCustom.__init__(self)

    @staticmethod
    def bootstrap_bat_args():
        return ['gcc']

    @staticmethod
    def bootstrap_sh_args():
        return ['--with-toolset=gcc']

    @staticmethod
    def b2_build_options():
        return []

    def cmake_format_config(self, platform):
        return f'''
set(CMAKE_C_COMPILER   gcc)
set(CMAKE_CXX_COMPILER g++)
{platform.cmake_toolset_file()}'''


def _gcc_or_auto():
    if shutil.which('gcc') is not None:
        return ['gcc']
    return []


class MinGW(BoostCustom, CMakeCustom):
    # It's important that Boost.Build is actually smart enough to detect the
    # GCC prefix (like "x86_64-w64-mingw32" and prepend it to other tools like
    # "ar").

    def __init__(self, platform):
        self.paths = project.mingw.MinGW(platform)
        BoostCustom.__init__(self, 'gcc', self.paths.gxx(), self.b2_build_options())
        CMakeCustom.__init__(self)

    @staticmethod
    def bootstrap_bat_args():
        # On Windows, prefer GCC if it's available.
        return _gcc_or_auto()

    @staticmethod
    def bootstrap_sh_args():
        return []

    @staticmethod
    def b2_build_options():
        return GCC.b2_build_options()

    def cmake_format_config(self, platform):
        return f'''
set(CMAKE_C_COMPILER   {self.paths.gcc()})
set(CMAKE_CXX_COMPILER {self.paths.gxx()})
set(CMAKE_AR           {self.paths.ar()})
set(CMAKE_RANLIB       {self.paths.ranlib()})
set(CMAKE_RC_COMPILER  {self.paths.windres()})
set(CMAKE_SYSTEM_NAME  Windows)
'''


class Clang(BoostCustom, CMakeCustom):
    def __init__(self):
        BoostCustom.__init__(self, 'clang', 'clang++', self.b2_build_options())
        CMakeCustom.__init__(self)

    @staticmethod
    def bootstrap_bat_args():
        # As of 1.74.0, bootstrap.bat isn't really aware of Clang, so try GCC,
        # then auto-detect.
        return _gcc_or_auto()

    @staticmethod
    def bootstrap_sh_args():
        # bootstrap.sh, on the other hand, is very much aware of Clang, and
        # it can build b2 using this compiler.
        return ['--with-toolset=clang']

    @staticmethod
    def b2_build_options():
        options = GCC.b2_build_options()
        options += [
            ('cxxflags', '-DBOOST_USE_WINDOWS_H'),

            # Even with <warnings>off, the build might sometimes fail with the
            # following error:
            #
            #     error: constant expression evaluates to -105 which cannot be narrowed to type 'boost::re_detail::cpp_regex_traits_implementation<char>::char_class_type' (aka 'unsigned int')
            ('cxxflags', '-Wno-c++11-narrowing'),
        ]
        if on_windows():
            # Prefer LLVM binutils:
            if shutil.which('llvm-ar') is not None:
                options.append(('archiver', 'llvm-ar'))
            if shutil.which('llvm-ranlib') is not None:
                options.append(('ranlib', 'llvm-ranlib'))
        return options

    def b2_format_config(self):
        # To make clang.exe/clang++.exe work on Windows, some tweaks are
        # required.  I borrowed them from CMake's Windows-Clang.cmake [1].
        # Adding them globally to Boost.Build options is described in [2].
        #
        # [1]: https://github.com/Kitware/CMake/blob/v3.18.4/Modules/Platform/Windows-Clang.cmake
        # [2]: https://stackoverflow.com/questions/2715106/how-to-create-a-new-variant-in-bjam
        return f'''project : requirements
    <target-os>windows:<define>_MT
    <target-os>windows,<variant>debug:<define>_DEBUG
    <target-os>windows,<runtime-link>static,<variant>debug:<cxxflags>"-Xclang -flto-visibility-public-std -Xclang --dependent-lib=libcmtd"
    <target-os>windows,<runtime-link>static,<variant>release:<cxxflags>"-Xclang -flto-visibility-public-std -Xclang --dependent-lib=libcmt"
    <target-os>windows,<runtime-link>shared,<variant>debug:<cxxflags>"-D_DLL -Xclang --dependent-lib=msvcrtd"
    <target-os>windows,<runtime-link>shared,<variant>release:<cxxflags>"-D_DLL -Xclang --dependent-lib=msvcrt"
;
{BoostCustom.b2_format_config(self)}
'''

    def cmake_format_config(self, platform):
        return f'''
if(CMAKE_VERSION VERSION_LESS "3.15" AND WIN32)
    set(CMAKE_C_COMPILER   clang-cl)
    set(CMAKE_CXX_COMPILER clang-cl)
else()
    set(CMAKE_C_COMPILER   clang)
    set(CMAKE_CXX_COMPILER clang++)
endif()
{platform.cmake_toolset_file()}'''

    @staticmethod
    def cmake_generator():
        return CMakeCustom.nmake_or_makefiles()


class ClangCL(CMakeCustom):
    @contextmanager
    def b2_args(self):
        yield [
            'toolset=clang-win',
            'define=BOOST_USE_WINDOWS_H',
        ]

    # There's no point in building b2 using clang-cl; clang though, presumably
    # installed alongside clang-cl, should still be used if possible.

    @staticmethod
    def bootstrap_bat_args():
        return Clang.bootstrap_bat_args()

    @staticmethod
    def bootstrap_sh_args():
        return Clang.bootstrap_sh_args()

    def cmake_format_config(self, platform):
        return f'''
set(CMAKE_C_COMPILER   clang-cl)
set(CMAKE_CXX_COMPILER clang-cl)
set(CMAKE_SYSTEM_NAME  Windows)
{platform.cmake_toolset_file()}'''

    @staticmethod
    def cmake_generator():
        return Clang.cmake_generator()
