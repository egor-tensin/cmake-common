# Copyright (c) 2020 Egor Tensin <egor@tensin.name>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common
# Distributed under the MIT License.

from enum import StrEnum
import platform


class OS(StrEnum):
    WINDOWS = "Windows"
    LINUX = "Linux"
    MACOS = "Darwin"

    @staticmethod
    def current():
        system = platform.system()
        try:
            return OS(system)
        except ValueError:
            raise NotImplementedError(f"unsupported OS: {system}")


def on_windows():
    return OS.current() is OS.WINDOWS


def on_windows_like():
    os = OS.current()
    return os is OS.WINDOWS


def on_linux():
    return OS.current() is OS.LINUX


def on_linux_like():
    os = OS.current()
    return os is OS.LINUX or os is OS.MACOS
