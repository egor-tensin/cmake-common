# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# Hate speech
# -----------
#
# Is there a person who doesn't hate Boost.Build?  I'm not sure, I'm definitely
# _not_ one of these people.  Maybe it's the lack of adoption (meaning that
# learning it is useless outside of Boost), maybe it's the incomprehensible
# syntax.  Maybe it's the absolutely insane compiler-specific configuration
# files (tools/build/src/tools/*.jam), which are impossible to figure out.
# Maybe it's the fact that the implementation switched from C to C++ while some
# half-baked Python implementation has been there since at least 2015 (see the
# marvelous memo "Status: mostly ported." at the top of tools/build/src/build_system.py).
#
# What I hate the most though is how its various subtle, implicit and invisible
# decision-making heuristics changed thoughout the release history of Boost.
# You have a config and a compiler that will happily build version 1.65.0?
# Great!  Want to use the same config and the same compiler to build version
# 1.72.0?  Well, too fucking bad, it doesn't work anymore.  This I really do
# hate the most.
#
# Three kinds of toolsets
# -----------------------
#
# b2 accepts the toolset= parameter.  What about building b2 itself though?
# Well, this is what the bootstrap.{sh,bat} scripts do.  They also accept a
# toolset argument, but it is _completely_ different to that of b2.  That's
# sort of OK, since e.g. cross-compiling b2 is something we rarely want to do
# (and hence there must typically be a native toolset available).
#
# bootstrap.sh and bootstrap.bat are completely different (of course!), and
# accept different arguments for their toolset parameters.
#
# Config file insanity
# --------------------
#
# Say, we're building Boost on Windows using the GCC from a MinGW-w64
# distribution.  We can pass toolset=gcc and all the required flags on the
# command line no problem.  What if we want to make a user configuration file
# so that 1) the command line is less polluted, and 2) it can possibly be
# shared?  Well, if we put
#
#     using gcc : : : <name>value... ;
#
# there, Boost 1.65.0 will happily build everything, while Boost 1.72.0 will
# complain about "duplicate initialization of gcc".  This is because when we
# ran `bootstrap.bat gcc` earlier, it wrote `using gcc ;` in project-config.jam.
# And while Boost 1.65.0 detects that toolset=gcc means we're going to use the
# MinGW GCC, and magically turns toolset=gcc to toolset=gcc-mingw, Boost 1.72.0
# does no such thing, and chokes on the "duplicate" GCC declaration.
#
# We also cannot put
#
#     using gcc : custom : : <options> ;
#
# without the executable path, since Boost insists that `g++ -dumpversion` must
# equal to "custom" (which makes total sense, lol).  So we have to force it,
# and do provide the path.
#
# Windows & Clang
# ---------------
#
# Building Boost using Clang on Windows is a sad story.  As of 2020, there're
# three main ways to install the native Clang toolchain on Windows:
#
#   * download the installer from llvm.org (`choco install llvm` does this)
#     a.k.a. the upstream,
#   * install it as part of a MSYS2 installation (`pacman -S mingw-w64-x86_64-clang`),
#   * install as part of a Visual Studio installation.
#
# Using the latter method, you can switch a project to use the LLVM toolset
# using Visual Studio, but that's stupid.  The former two, on the other hand,
# give us the the required clang/clang++/clang-cl executables, so everything
# seems to be fine.
#
# Except it's not fine.  Let's start with the fact that prior to 1.66.0,
# toolset=clang is completely broken on Windows.  It's just an alias for
# clang-linux, and it's hardcoded to require the ar & ranlib executables to
# create static libraries.  Which is fine on Linux, since, and I'm quoting the
# source, "ar is always available".  But it's not fine on Windows, since
# ar/ranlib are not, in fact, available there by default.  Sure, you can
# install some kind of MinGW toolchain, and it might even work, but what the
# hell, honestly?
#
# Luckily, both the upstream distribution and the MSYS2 mingw-w64-x86_64-llvm
# package come with the llvm-ar and llvm-ranlib utilities.  So we can put
# something like this in the config:
#
#     using clang : custom : clang++.exe : <archiver>llvm-ar <ranlib>llvm-ranlib.exe ;
#
# and later call
#
#     b2 toolset=clang-custom --user-config=path/to/config.jam ...
#
# But, as I mentioned, prior to 1.66.0, toolset=clang is _hardcoded_ to use ar
# & ranlib, these exact utility names.  So either get them as part of some
# MinGW distribution or build Boost using another toolset.
#
# Now, it's all fine, but building stuff on Windows adds another thing into the
# equation: debug runtimes.  When you build Boost using MSVC, for example, it
# picks one of the appropriate /MT[d] or /MD[d] flags to build the Boost
# libraries with.  Emulating these flags with toolset=clang is complicated and
# inconvenient.  Luckily, there's the clang-cl.exe executable, which aims to
# provide command line interface compatible with that of cl.exe.
#
# Boost.Build even supports toolset=clang-win, which should use clang-cl.exe.
# But alas, it's completely broken prior to 1.69.0.  It just doesn't work at
# all.  So, if you want to build w/ clang-cl.exe, either use Boost 1.69.0 or
# later, or build using another toolset.
#
# Cygwin & Clang
# --------------
#
# Now, a few words about Clang on Cygwin.  When building 1.65.0, I encountered
# the following error:
#
#     /usr/include/w32api/synchapi.h:127:26: error: conflicting types for 'Sleep'
#       WINBASEAPI VOID WINAPI Sleep (DWORD dwMilliseconds);
#                              ^
#     ./boost/smart_ptr/detail/yield_k.hpp:64:29: note: previous declaration is here
#       extern "C" void __stdcall Sleep( unsigned long ms );
#                                 ^
#
# GCC doesn't emit an error here because /usr/include is in a pre-configured
# "system" include directories list, and the declaration there take precedence,
# I guess?  The root of the problem BTW is that sizeof(unsigned long) is
#
#   * 4 for MSVC and MinGW-born GCCs,
#   * 8 for Clang (and, strangely, Cygwin GCC; why don't we get runtime
#     errors?).
#
# The fix is to add `define=BOOST_USE_WINDOWS_H`.  I don't even know what's the
# point of not having it as a default.

import abc
from contextlib import contextmanager
import logging
import os.path
import shutil

import project.mingw
import project.os
from project.toolchain import ToolchainType
from project.utils import temp_file


class BootstrapToolchain(abc.ABC):
    @abc.abstractmethod
    def get_bootstrap_bat_args(self):
        pass

    @abc.abstractmethod
    def get_bootstrap_sh_args(self):
        pass

    @staticmethod
    def detect(hint):
        if hint is ToolchainType.AUTO:
            return BootstrapAuto()
        if hint is ToolchainType.MSVC:
            return BootstrapMSVC()
        if hint is ToolchainType.GCC:
            return BootstrapGCC()
        if hint is ToolchainType.MINGW:
            return BootstrapMinGW()
        if hint is ToolchainType.CLANG:
            return BootstrapClang()
        if hint is ToolchainType.CLANG_CL:
            return BootstrapClangCL()
        raise NotImplementedError(f'unrecognized toolset: {hint}')


class BootstrapAuto(BootstrapToolchain):
    # Let Boost.Build do the detection.  Most commonly it means GCC on
    # Linux-likes and MSVC on Windows.

    def get_bootstrap_bat_args(self):
        return []

    def get_bootstrap_sh_args(self):
        return []


class BootstrapMSVC(BootstrapAuto):
    # bootstrap.bat picks up MSVC by default.
    pass


class BootstrapGCC(BootstrapToolchain):
    def get_bootstrap_bat_args(self):
        return ['gcc']

    def get_bootstrap_sh_args(self):
        return ['--with-toolset=gcc']


def _gcc_or_auto():
    if shutil.which('gcc') is not None:
        return ['gcc']
    return []


class BootstrapMinGW(BootstrapToolchain):
    def get_bootstrap_bat_args(self):
        # On Windows, prefer GCC if it's available.
        return _gcc_or_auto()

    def get_bootstrap_sh_args(self):
        return []


class BootstrapClang(BootstrapToolchain):
    def get_bootstrap_bat_args(self):
        # As of 1.74.0, bootstrap.bat isn't really aware of Clang, so try GCC,
        # then auto-detect.
        return _gcc_or_auto()

    def get_bootstrap_sh_args(self):
        # bootstrap.sh, on the other hand, is very much aware of Clang, and
        # it can build b2 using this compiler.
        return ['--with-toolset=clang']


class BootstrapClangCL(BootstrapClang):
    # There's no point in building b2 using clang-cl; clang though, presumably
    # installed alongside clang-cl, should still be used if possible.
    pass


class Toolchain(abc.ABC):
    def __init__(self, platform):
        self.platform = platform

    def get_b2_args(self):
        return [
            # Always pass the address-model explicitly.
            f'address-model={self.platform.get_address_model()}'
        ]

    @staticmethod
    @contextmanager
    def detect(hint, platform):
        if hint is ToolchainType.AUTO:
            yield Auto(platform)
        elif hint is ToolchainType.MSVC:
            yield MSVC(platform)
        elif hint is ToolchainType.GCC:
            with GCC.setup(platform) as toolchain:
                yield toolchain
        elif hint is ToolchainType.MINGW:
            with MinGW.setup(platform) as toolchain:
                yield toolchain
        elif hint is ToolchainType.CLANG:
            with Clang.setup(platform) as toolchain:
                yield toolchain
        elif hint is ToolchainType.CLANG_CL:
            yield ClangCL(platform)
        else:
            raise NotImplementedError(f'unrecognized toolset: {hint}')


class Auto(Toolchain):
    # Let Boost.Build do the detection.  Most commonly it means GCC on
    # Linux-likes and MSVC on Windows.
    pass


class MSVC(Auto):
    def get_b2_args(self):
        return super().get_b2_args() + [
            'toolset=msvc',
        ]


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


class BoostBuildToolset:
    CUSTOM = 'custom'

    def __init__(self, compiler, path, options):
        if not compiler:
            raise RuntimeError('compiler type is required (like gcc, clang, etc.)')
        self.compiler = compiler
        self.version = BoostBuildToolset.CUSTOM
        path = path or ''
        path = path and _full_exe_name(path)
        self.path = path
        options = options or []
        self.options = options

    @property
    def toolset_id(self):
        if self.version:
            return f'{self.compiler}-{self.version}'
        return self.compiler

    @property
    def b2_arg(self):
        return f'toolset={self.toolset_id}'

    def _format_using_options(self):
        return ''.join(f'\n    <{name}>{val}' for name, val in self.options)

    def format_using(self):
        version = self.version and f'{self.version} '
        path = self.path and f'{self.path} '
        return f'''using {self.compiler} : {version}: {path}:{self._format_using_options()}
;'''


class ConfigFile(Toolchain):
    def __init__(self, platform, config_path, toolset):
        super().__init__(platform)
        self.config_path = config_path
        self.toolset = toolset

    @staticmethod
    @abc.abstractmethod
    def get_toolset(platform):
        pass

    @staticmethod
    @abc.abstractmethod
    def format_config(toolset):
        pass

    @classmethod
    @contextmanager
    def setup(cls, platform):
        toolset = cls.get_toolset(platform)
        config = cls.format_config(toolset)
        logging.info('Using user config:\n%s', config)
        tmp = temp_file(config, mode='w', prefix='user_config_', suffix='.jam')
        with tmp as path:
            yield cls(platform, path, toolset)

    def get_b2_args(self):
        # All the required options and the toolset definition should be in the
        # user configuration file.
        return super().get_b2_args() + [
            f'--user-config={self.config_path}',
            self.toolset.b2_arg,
        ]


class GCC(ConfigFile):
    # Force GCC.  We don't care whether it's a native Linux GCC or a
    # MinGW-flavoured GCC on Windows.
    COMPILER = 'gcc'

    @staticmethod
    def get_options():
        return [
            # TODO: this is a petty attempt to get rid of build warnings in
            # older Boost versions.  Revise and expand this list or remove it?
            # warning: 'template<class> class std::auto_ptr' is deprecated
            ('cxxflags', '-Wno-deprecated-declarations'),
            # warning: unnecessary parentheses in declaration of 'assert_arg'
            ('cxxflags', '-Wno-parentheses'),
        ]

    @staticmethod
    def get_toolset(platform):
        return BoostBuildToolset(GCC.COMPILER, 'g++', GCC.get_options())

    @staticmethod
    def format_config(toolset):
        return toolset.format_using()


class MinGW(GCC):
    # It's important that Boost.Build is actually smart enough to detect the
    # GCC prefix (like "x86_64-w64-mingw32" and prepend it to other tools like
    # "ar").

    @staticmethod
    def get_toolset(platform):
        path = project.mingw.get_gxx(platform)
        return BoostBuildToolset(MinGW.COMPILER, path, MinGW.get_options())


class Clang(ConfigFile):
    COMPILER = 'clang'

    @staticmethod
    def get_toolset(platform):
        options = [
            ('cxxflags', '-DBOOST_USE_WINDOWS_H'),
            # TODO: this is a petty attempt to get rid of build warnings in
            # older Boost versions.  Revise and expand this list or remove it?
            # warning: unused typedef 'boost_concept_check464' [-Wunused-local-typedef]
            ('cxxflags', '-Wno-unused-local-typedef'),
            # error: constant expression evaluates to -105 which cannot be narrowed to type 'boost::re_detail::cpp_regex_traits_implementation<char>::char_class_type' (aka 'unsigned int')
            ('cxxflags', '-Wno-c++11-narrowing'),
        ] + GCC.get_options()
        if project.os.on_windows():
            # Prefer LLVM binutils:
            if shutil.which('llvm-ar') is not None:
                options.append(('archiver', 'llvm-ar'))
            if shutil.which('llvm-ranlib') is not None:
                options.append(('ranlib', 'llvm-ranlib'))
        return BoostBuildToolset(Clang.COMPILER, 'clang++', options)

    @staticmethod
    def format_config(toolset):
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
{toolset.format_using()}
'''


class ClangCL(Toolchain):
    def get_b2_args(self):
        return super().get_b2_args() + [
            'toolset=clang-win',
            'define=BOOST_USE_WINDOWS_H',
        ]
