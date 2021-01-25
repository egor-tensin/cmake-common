# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from enum import Enum

from project.utils import env


class Image(Enum):
    VS_2013 = 'Visual Studio 2013'
    VS_2015 = 'Visual Studio 2015'
    VS_2017 = 'Visual Studio 2017'
    VS_2019 = 'Visual Studio 2019'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def parse(s):
        try:
            return Image(s)
        except ValueError as e:
            raise ValueError(f'unsupported AppVeyor image: {s}') from e

    @staticmethod
    def get():
        return Image.parse(env('APPVEYOR_BUILD_WORKER_IMAGE'))

    def get_prebuilt_boost_dir(self):
        # As of 2021-01-25, these are the latest pre-built Boost distributions:
        # https://www.appveyor.com/docs/windows-images-software/#boost
        if self is Image.VS_2013:
            return 'C:\\Libraries\\boost_1_58_0'
        if self is Image.VS_2015:
            return 'C:\\Libraries\\boost_1_69_0'
        if self is Image.VS_2017:
            return 'C:\\Libraries\\boost_1_69_0'
        if self is Image.VS_2019:
            return 'C:\\Libraries\\boost_1_73_0'
        raise NotImplementedError(f'unsupported AppVeyor image: {self}')


class Generator(Enum):
    VS_2013 = 'Visual Studio 12 2013'
    VS_2015 = 'Visual Studio 14 2015'
    VS_2017 = 'Visual Studio 15 2017'
    VS_2019 = 'Visual Studio 16 2019'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def from_image(image):
        if image is Image.VS_2013:
            return Generator.VS_2013
        if image is Image.VS_2015:
            return Generator.VS_2015
        if image is Image.VS_2017:
            return Generator.VS_2017
        if image is Image.VS_2019:
            return Generator.VS_2019
        raise RuntimeError(f"don't know which generator to use for image: {image}")
