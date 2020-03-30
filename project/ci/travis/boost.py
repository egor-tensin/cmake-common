# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

from project.ci.boost import build_ci
from project.ci.dirs import Travis
from project.utils import setup_logging


def main(argv=None):
    with setup_logging():
        build_ci(Travis(), argv)


if __name__ == '__main__':
    main()
