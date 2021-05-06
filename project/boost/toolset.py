# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# See docs/boost.md for a more thorough description of my pain.

import abc
from contextlib import contextmanager
import logging
import os.path
import shutil

import project.mingw
import project.os
from project.toolset import ToolchainType
from project.utils import temp_file


def _gcc_or_auto():
    if shutil.which('gcc') is not None:
        return ['gcc']
    return []


class Toolchain(abc.ABC):
    @contextmanager
    def b2_args(self):
        # Write the config file, etc.
        yield []

    @staticmethod
    @abc.abstractmethod
    def get_bootstrap_bat_args():
        pass

    @staticmethod
    @abc.abstractmethod
    def get_bootstrap_sh_args():
        pass

    @staticmethod
    def detect(hint):
        if hint is ToolchainType.AUTO:
            return Auto
        if hint is ToolchainType.MSVC:
            return MSVC
        if hint is ToolchainType.GCC:
            return GCC
        if hint is ToolchainType.MINGW:
            return MinGW
        if hint is ToolchainType.CLANG:
            return Clang
        if hint is ToolchainType.CLANG_CL:
            return ClangCL
        raise NotImplementedError(f'unrecognized toolset: {hint}')

    @staticmethod
    def make(hint, platform):
        # Platform is required here, since some toolchains (MinGW-w64) require
        # it for the compiler path.
        cls = Toolchain.detect(hint)
        if cls is MinGW:
            return MinGW(platform)
        return cls()


class Auto(Toolchain):
    # Let Boost.Build do the detection.  Most commonly it means GCC on
    # Linux-likes and MSVC on Windows.

    @staticmethod
    def get_bootstrap_bat_args():
        return []

    @staticmethod
    def get_bootstrap_sh_args():
        return []


class MSVC(Auto):
    @contextmanager
    def b2_args(self):
        yield ['toolset=msvc']

    # Note: bootstrap.bat picks up MSVC by default.


def _full_exe_name(exe):
    if project.os.on_linux():
        # There's no PATHEXT on Linux.
        return exe
    # b2 on Windows/Cygwin doesn't like it when the executable name doesn't
    # include the extension.
    dir_path = os.path.dirname(exe) or None
    path = shutil.which(exe, path=dir_path)
    if not path:
        raise RuntimeError(f"executable '{exe}' could not be found")
    if project.os.on_cygwin():
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


class Custom(Toolchain):
    COMPILER_VERSION = 'custom'

    def __init__(self, compiler, path=None, build_options=None):
        if not compiler:
            raise RuntimeError('compiler type is required (like gcc, clang, etc.)')
        self.compiler = compiler
        version = Custom.COMPILER_VERSION
        self.version = version
        path = path or ''
        path = path and _full_exe_name(path)
        self.path = path
        build_options = build_options or []
        self.build_options = build_options

    def toolset(self):
        if self.version:
            return f'{self.compiler}-{self.version}'
        return self.compiler

    def b2_arg_toolset(self):
        return f'toolset={self.toolset()}'

    def _format_build_options(self):
        return ''.join(f'\n    <{name}>{val}' for name, val in self.build_options)

    def format_config(self):
        version = self.version and f'{self.version} '
        path = self.path and f'{self.path} '
        return f'''using {self.compiler} : {version}: {path}:{self._format_build_options()}
;'''

    @contextmanager
    def b2_args(self):
        config_file = temp_file(prefix='user_config_', suffix='.jam')
        with config_file as config_path:
            config = self.format_config()
            logging.info('Using user config:\n%s', config)
            with open(config_path, mode='w') as fd:
                fd.write(config)
            args = []
            args.append(self.b2_arg_toolset())
            args.append(f'--user-config={config_path}')
            yield args


class GCC(Custom):
    # Force GCC.  We don't care whether it's a native Linux GCC or a
    # MinGW-flavoured GCC on Windows.
    def __init__(self, path='g++', build_options=None):
        build_options = build_options or self.get_build_options()
        super().__init__('gcc', path, build_options)

    @staticmethod
    def get_bootstrap_bat_args():
        return ['gcc']

    @staticmethod
    def get_bootstrap_sh_args():
        return ['--with-toolset=gcc']

    @staticmethod
    def get_build_options():
        return []


class MinGW(GCC):
    # It's important that Boost.Build is actually smart enough to detect the
    # GCC prefix (like "x86_64-w64-mingw32" and prepend it to other tools like
    # "ar").

    def __init__(self, platform):
        paths = project.mingw.MinGW(platform)
        super().__init__(paths.gxx())

    @staticmethod
    def get_bootstrap_bat_args():
        # On Windows, prefer GCC if it's available.
        return _gcc_or_auto()

    @staticmethod
    def get_bootstrap_sh_args():
        return []


class Clang(Custom):
    def __init__(self):
        super().__init__('clang', 'clang++', self.get_build_options())

    @staticmethod
    def get_bootstrap_bat_args():
        # As of 1.74.0, bootstrap.bat isn't really aware of Clang, so try GCC,
        # then auto-detect.
        return _gcc_or_auto()

    @staticmethod
    def get_bootstrap_sh_args():
        # bootstrap.sh, on the other hand, is very much aware of Clang, and
        # it can build b2 using this compiler.
        return ['--with-toolset=clang']

    @staticmethod
    def get_build_options():
        options = GCC.get_build_options()
        options += [
            ('cxxflags', '-DBOOST_USE_WINDOWS_H'),

            # Even with <warnings>off, the build might sometimes fail with the
            # following error:
            #
            #     error: constant expression evaluates to -105 which cannot be narrowed to type 'boost::re_detail::cpp_regex_traits_implementation<char>::char_class_type' (aka 'unsigned int')
            ('cxxflags', '-Wno-c++11-narrowing'),
        ]
        if project.os.on_windows():
            # Prefer LLVM binutils:
            if shutil.which('llvm-ar') is not None:
                options.append(('archiver', 'llvm-ar'))
            if shutil.which('llvm-ranlib') is not None:
                options.append(('ranlib', 'llvm-ranlib'))
        return options

    def format_config(self):
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
{super().format_config()}
'''


class ClangCL(Toolchain):
    @contextmanager
    def b2_args(self):
        yield [
            'toolset=clang-win',
            'define=BOOST_USE_WINDOWS_H',
        ]

    # There's no point in building b2 using clang-cl; clang though, presumably
    # installed alongside clang-cl, should still be used if possible.

    @staticmethod
    def get_bootstrap_bat_args():
        return Clang.get_bootstrap_bat_args()

    @staticmethod
    def get_bootstrap_sh_args():
        return Clang.get_bootstrap_sh_args()
