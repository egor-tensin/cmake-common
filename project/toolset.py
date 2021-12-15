# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

'''Supported platform/build system/compiler combinations include, but are not
limited to:

| Platform | Build system | Compiler  |
| -------- | ------------ | --------- |
| Linux    | make         | Clang     |
|          |              | GCC       |
|          |              | MinGW-w64 |
| Windows  | make [1]     | Clang [2] |
|          |              | MinGW-w64 |
|          | msbuild      | MSVC      |
| Cygwin   | make         | Clang     |
|          |              | GCC       |
|          |              | MinGW-w64 |

1. Both GNU make and MinGW mingw32-make.
2. clang-cl is supported by Boost 1.69.0 or higher only.
'''

# See docs/{boost,cmake}.md for a more thorough description of my pain.

import abc
import argparse
from contextlib import contextmanager
from decimal import Decimal
from enum import Enum
import logging
import os.path
import shutil

import project.mingw
from project.os import on_windows
from project.platform import Platform
from project.utils import full_exe_name, temp_file


class MSVCVersion(Enum):
    # It's the MSVC "toolset" version, or whatever.
    # Source: https://cmake.org/cmake/help/v3.20/variable/MSVC_TOOLSET_VERSION.html#variable:MSVC_TOOLSET_VERSION

    VS2010 = '100'
    VS2012 = '110'
    VS2013 = '120'
    VS2015 = '140'
    VS2017 = '141'
    VS2019 = '142'
    VS2022 = '143'

    def __str__(self):
        return str(self.value)

    def help(self):
        if self is MSVCVersion.VS2010:
            return 'Visual Studio 2010'
        if self is MSVCVersion.VS2012:
            return 'Visual Studio 2012'
        if self is MSVCVersion.VS2013:
            return 'Visual Studio 2013'
        if self is MSVCVersion.VS2015:
            return 'Visual Studio 2015'
        if self is MSVCVersion.VS2017:
            return 'Visual Studio 2017'
        if self is MSVCVersion.VS2019:
            return 'Visual Studio 2019'
        if self is MSVCVersion.VS2022:
            return 'Visual Studio 2022'
        raise NotImplementedError(f'unsupported MSVC version: {self}')

    @staticmethod
    def parse(s):
        try:
            return MSVCVersion(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid MSVC version: {s}') from e

    @staticmethod
    def all():
        return tuple(MSVCVersion)

    def to_msvc_version(self):
        return self

    def to_visual_studio_version(self):
        if MSVCVersion.VS2010:
            return VisualStudioVersion.VS2010
        if MSVCVersion.VS2012:
            return VisualStudioVersion.VS2012
        if MSVCVersion.VS2013:
            return VisualStudioVersion.VS2013
        if MSVCVersion.VS2015:
            return VisualStudioVersion.VS2015
        if MSVCVersion.VS2017:
            return VisualStudioVersion.VS2017
        if MSVCVersion.VS2019:
            return VisualStudioVersion.VS2019
        if MSVCVersion.VS2022:
            return VisualStudioVersion.VS2022
        raise NotImplementedError(f'unsupported MSVC version: {self}')

    def to_boost_msvc_version(self):
        try:
            numeric = int(self.value)
        except ValueError:
            raise RuntimeError(f'what? MSVC versions are supposed to be integers: {self.value}')
        numeric = Decimal(numeric) / 10
        numeric = numeric.quantize(Decimal('1.0'))
        return str(numeric)

    def to_cmake_toolset(self):
        return f'v{self}'


class VisualStudioVersion(Enum):
    VS2010 = '2010'
    VS2012 = '2012'
    VS2013 = '2013'
    VS2015 = '2015'
    VS2017 = '2017'
    VS2019 = '2019'
    VS2022 = '2022'

    def __str__(self):
        return str(self.value)

    def help(self):
        if self is VisualStudioVersion.VS2010:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2010}'"
        if self is VisualStudioVersion.VS2012:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2012}'"
        if self is VisualStudioVersion.VS2013:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2013}'"
        if self is VisualStudioVersion.VS2015:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2015}'"
        if self is VisualStudioVersion.VS2017:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2017}'"
        if self is VisualStudioVersion.VS2019:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2019}'"
        if self is VisualStudioVersion.VS2022:
            return f"Same as '{ToolsetType.MSVC}{MSVCVersion.VS2022}'"
        raise NotImplementedError(f'unsupported Visual Studio version: {self}')

    @staticmethod
    def parse(s):
        try:
            return VisualStudioVersion(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid Visual Studio version: {s}') from e

    @staticmethod
    def all():
        return tuple(VisualStudioVersion)

    def to_msvc_version(self):
        if self is VisualStudioVersion.VS2010:
            return MSVCVersion.VS2010
        if self is VisualStudioVersion.VS2012:
            return MSVCVersion.VS2012
        if self is VisualStudioVersion.VS2013:
            return MSVCVersion.VS2013
        if self is VisualStudioVersion.VS2015:
            return MSVCVersion.VS2015
        if self is VisualStudioVersion.VS2017:
            return MSVCVersion.VS2017
        if self is VisualStudioVersion.VS2019:
            return MSVCVersion.VS2019
        if self is VisualStudioVersion.VS2022:
            return MSVCVersion.VS2022
        raise NotImplementedError(f'unsupported Visual Studio version: {self}')

    def to_visual_studio_version(self):
        return self


class ToolsetType(Enum):
    AUTO = 'auto'
    MSVC = 'msvc'
    VISUAL_STUDIO = 'vs'
    GCC = 'gcc'
    MINGW = 'mingw'
    CLANG = 'clang'
    CLANG_CL = 'clang-cl'

    def __str__(self):
        return str(self.value)

    def help(self):
        if self is ToolsetType.AUTO:
            return "Means 'gcc' on Linux and 'msvc' on Windows"
        if self is ToolsetType.MSVC:
            return 'Use cl.exe'
        if self is ToolsetType.VISUAL_STUDIO:
            return "Visual Studio; same as 'msvc'"
        if self is ToolsetType.GCC:
            return 'Use gcc/g++'
        if self is ToolsetType.MINGW:
            return 'Use gcc/g++ with the PLATFORM-w64-mingw32 prefix'
        if self is ToolsetType.CLANG:
            return 'Use clang/clang++'
        if self is ToolsetType.CLANG_CL:
            return 'Use clang-cl.exe'
        raise NotImplementedError(f'unsupported toolset: {self}')

    @staticmethod
    def parse(s):
        try:
            return ToolsetType(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f'invalid toolset: {s}') from e

    @property
    def is_versioned(self):
        if self is ToolsetType.MSVC or self is ToolsetType.VISUAL_STUDIO:
            return True
        return False

    def parse_version(self, s):
        if self is ToolsetType.MSVC:
            return MSVCVersion.parse(s)
        if self is ToolsetType.VISUAL_STUDIO:
            return VisualStudioVersion.parse(s)
        raise RuntimeError(f"this toolset doesn't support versions: {self}")

    def all_versions(self):
        if self is ToolsetType.MSVC:
            return MSVCVersion.all()
        if self is ToolsetType.VISUAL_STUDIO:
            return VisualStudioVersion.all()
        raise RuntimeError(f"this toolset doesn't support versions: {self}")

    @staticmethod
    def all():
        return tuple(ToolsetType)

    @staticmethod
    def all_versioned():
        return (t for t in ToolsetType.all() if t.is_versioned)

    @staticmethod
    def all_unversioned():
        return (t for t in ToolsetType.all() if not t.is_versioned)


class ToolsetVersion:
    def __init__(self, hint, version):
        self.hint = hint
        self.version = version

    def __str__(self):
        if self.version is None:
            return str(self.hint)
        return f'{self.hint}{self.version}'

    @staticmethod
    def default():
        return ToolsetVersion(ToolsetType.AUTO, None)

    @staticmethod
    def usage():
        return '/'.join(map(str, ToolsetType.all()))

    @staticmethod
    def help_toolsets():
        return f'''{__doc__}
{ToolsetVersion.help_all_toolsets()}
{ToolsetVersion.help_versioned_toolsets()}'''

    @staticmethod
    def help_all_toolsets():
        s = '''All supported toolsets are listed below.

'''
        max_name = max((len(str(hint)) for hint in ToolsetType.all()))
        for hint in ToolsetType.all():
            name_padding = ' ' * (max_name - len(str(hint)))
            s += f'  * {hint}{name_padding} \t{hint.help()}\n'
        return s

    @staticmethod
    def help_versioned_toolsets():
        s = '''Some toolsets support specifying a version using the VERSION suffix.  This is
a list of all supported toolset versions:

'''
        max_name = max((len(str(hint) + str(version)) for hint in ToolsetType.all_versioned() for version in hint.all_versions()))
        for hint in ToolsetType.all_versioned():
            for version in hint.all_versions():
                name = f'{hint}{version}'
                name_padding = ' ' * (max_name - len(name))
                s += f'  * {name}{name_padding} \t{version.help()}\n'
        return s

    @staticmethod
    def parse(s):
        try:
            return ToolsetVersion(ToolsetType(s), None)
        except ValueError:
            pass
        for hint in sorted(ToolsetType.all_versioned(), key=str, reverse=True):
            prefix = f'{hint}'
            if s.startswith(prefix):
                return ToolsetVersion(hint, hint.parse_version(s[len(prefix):]))
        raise argparse.ArgumentTypeError(f'invalid toolset: {s}')


class Toolset(abc.ABC):
    @staticmethod
    @contextmanager
    def b2_args():
        # Write the config file, etc.
        yield []

    @staticmethod
    def bootstrap_bat_args():
        return []

    @staticmethod
    def bootstrap_sh_args():
        return []

    @staticmethod
    def cmake_generator():
        return None

    def cmake_args(self, build_dir, platform):
        args = []
        generator = self.cmake_generator()
        if generator is not None:
            args += ['-G', generator]
        return args

    @staticmethod
    def build_system_args():
        return []

    @staticmethod
    def detect(version):
        if version.hint is ToolsetType.AUTO:
            return Auto
        if version.hint is ToolsetType.MSVC or version.hint is ToolsetType.VISUAL_STUDIO:
            return MSVC
        if version.hint is ToolsetType.GCC:
            return GCC
        if version.hint is ToolsetType.MINGW:
            return MinGW
        if version.hint is ToolsetType.CLANG:
            return Clang
        if version.hint is ToolsetType.CLANG_CL:
            return ClangCL
        raise NotImplementedError(f'unrecognized toolset: {version}')

    @staticmethod
    def make(version, platform):
        # Platform is required here, since some toolsets (MinGW-w64) require
        # it for the compiler path.
        cls = Toolset.detect(version)
        if cls is MinGW:
            return MinGW(platform)
        if version.hint.is_versioned:
            return cls(version.version)
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
            return super().cmake_args(build_dir, platform)
        # If a specific platform was requested, we might need to set some
        # CMake/compiler flags, like -m32/-m64.
        return GCC().cmake_args(build_dir, platform)


class MSVC(Toolset):
    def __init__(self, version=None):
        self.version = version

    def b2_toolset(self):
        if self.version is not None:
            return f'msvc-{self.version.to_msvc_version().to_boost_msvc_version()}'
        return 'msvc'

    @contextmanager
    def b2_args(self):
        yield [f'toolset={self.b2_toolset()}']

    # Note: bootstrap.bat picks up MSVC by default.

    def cmake_args(self, build_dir, platform):
        # This doesn't actually specify the generator of course, but I don't
        # want to implement VS detection logic.
        args = super().cmake_args(build_dir, platform)
        args += ['-A', platform.msvc_arch()]
        if self.version is not None:
            args += ['-T', self.version.to_msvc_version().to_cmake_toolset()]
        return args


class BoostCustom(Toolset):
    COMPILER_VERSION = 'custom'

    def __init__(self, compiler, path=None, build_options=None):
        if not compiler:
            raise RuntimeError('compiler type is required (like gcc, clang, etc.)')
        self.compiler = compiler
        version = BoostCustom.COMPILER_VERSION
        self.version = version
        path = path or ''
        path = path and full_exe_name(path)
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
        # The Visual Studio generator is the default on Windows, override it:
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

        return super().cmake_args(build_dir, platform) + [
            f'-DCMAKE_TOOLCHAIN_FILE={config_path}',
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
