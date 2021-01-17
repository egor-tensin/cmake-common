# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from enum import Enum
import platform


class OS(Enum):
    WINDOWS = 'Windows'
    LINUX = 'Linux'
    CYGWIN = 'Cygwin'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def current():
        system = platform.system()
        if system == 'Windows':
            return OS.WINDOWS
        if system == 'Linux':
            return OS.LINUX
        if system.startswith('CYGWIN_NT'):
            return OS.CYGWIN
        raise NotImplementedError(f'unsupported OS: {system}')


def on_windows():
    return OS.current() is OS.WINDOWS


def on_windows_like():
    os = OS.current()
    return os is OS.WINDOWS or os is OS.CYGWIN


def on_linux():
    return OS.current() is OS.LINUX


def on_linux_like():
    os = OS.current()
    return os is OS.LINUX or os is OS.CYGWIN


def on_cygwin():
    return OS.current() is OS.CYGWIN
