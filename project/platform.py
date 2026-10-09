# Copyright (c) 2020 Egor Tensin <egor@tensin.name>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common
# Distributed under the MIT License.

import argparse
from enum import auto, StrEnum
import os.path
import platform

from project.os import on_windows


class Platform(StrEnum):
    # I only build for x86(-64), so here it goes.
    X86 = auto()
    X64 = auto()
    # 'auto' means that no additional arguments will be passed to either
    # Boost's b2 nor CMake (except on Windows, see below).
    AUTO = auto()

    @staticmethod
    def windows_native():
        # On Windows, no explicit platform would mean x64 for VS 2019 and x86
        # for VS 2017.  To account for this discrepancy, it is assumed that
        # Windows builds can only target either x86 or x64 (which I don't think
        # is true?), and we default to x64 most of the time.
        #
        # Source: https://stackoverflow.com/a/12578715/514684
        if platform.machine().endswith("64"):
            return Platform.X64
        return Platform.X86

    @staticmethod
    def all():
        return Platform.X86, Platform.X64

    @staticmethod
    def parse(s):
        try:
            if s == "Win32":
                # Visual Studio/AppVeyor convention:
                return Platform.X86
            return Platform(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"invalid platform: {s}") from e

    def mingw_prefix(self):
        match self:
            case Platform.AUTO if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().mingw_prefix()
            case Platform.AUTO:
                # On Linux, assume that the target is x64.
                return Platform.X64.mingw_prefix()
            case Platform.X86:
                return "i686"
            case Platform.X64:
                return "x86_64"
            case _:
                raise NotImplementedError(f"unsupported platform: {self}")

    def address_model(self):
        """Maps to Boost's address-model."""
        match self:
            case Platform.AUTO if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().address_model()
            case Platform.AUTO:
                # On Linux, assume that the target is x64.
                # FIXME: the comment above doesn't seem to reflect the code?
                raise RuntimeError(
                    "cannot determine address model unless the target platform is specified explicitly"
                )
            case Platform.X86:
                return 32
            case Platform.X64:
                return 64
            case _:
                raise NotImplementedError(f"unsupported platform: {self}")

    def installdir(self, configuration):
        """Path to the installation directory inside the Boost build directory."""
        match self:
            case Platform.AUTO if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().installdir(configuration)
            # On Linux, the libraries are stored in install_dir/auto/CONFIGURATION/lib.
            case _:
                return os.path.join("install_dir", self, configuration)

    def boost_installdir(self, configuration):
        """Same as above, but for CMake."""
        return self.installdir(configuration)

    def b2_address_model(self):
        match self:
            case Platform.AUTO if not on_windows():
                # On Linux, don't specify the architecture explicitly (it is
                # assumed that the host architecture will be targeted).
                return []
            case _:
                return [f"address-model={self.address_model()}"]

    def b2_installdir(self, configuration):
        return [f"--prefix={self.installdir(configuration)}"]

    def b2_args(self, configuration):
        args = []
        args += self.b2_address_model()
        args += self.b2_installdir(configuration)
        return args

    def cmake_toolset_file(self):
        # For Makefile generators, we make a special toolset file that
        # specifies the -m32/-m64 flags, etc.
        template = """
set(CMAKE_C_FLAGS   -m{bitness})
set(CMAKE_CXX_FLAGS -m{bitness})
"""
        match self:
            case Platform.AUTO:
                return ""
            case Platform.X86:
                return template.format(bitness=32)
            case Platform.X64:
                return template.format(bitness=64)
            case _:
                raise NotImplementedError(f"unsupported platform: {self}")

    def msvc_arch(self):
        """Maps to CMake's -A argument for MSVC."""
        match self:
            case Platform.AUTO if on_windows():
                # On Windows, use the host architecture.
                return Platform.windows_native().msvc_arch()
            case Platform.AUTO:
                # I don't think the -A argument is supported on any generators
                # except the Visual Studio ones.
                raise RuntimeError(
                    "-A parameter is only supported for Visual Studio generators"
                )
            case Platform.X86:
                return "Win32"
            case Platform.X64:
                return "x64"
            case _:
                raise NotImplementedError(f"unsupported platform: {self}")
