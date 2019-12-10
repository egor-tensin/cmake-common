#!/usr/bin/env bash

# Copyright (c) 2019 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# This script is used during a Travis build to download and build Boost.
# Input:
# * environment variables $travis_boost_version, $configuration and $platform.
# Output:
# * unpacked Boost distribution at $HOME/boost_X_YY_Z,
# * built libraries at $HOME/boost_X_YY_Z/stage/$platform/${configuration,,}.

set -o errexit -o nounset -o pipefail -o xtrace

readonly base_dir="$HOME"
readonly boost_fs="boost_${travis_boost_version//\./_}"
readonly boost_url="https://dl.bintray.com/boostorg/release/$travis_boost_version/source/$boost_fs.tar.gz"
readonly boost_dir="$base_dir/$boost_fs"

address_model=32
[ "$platform" = x64 ] && address_model=64
readonly address_model

configuration="${configuration,,}"
readonly configuration

download() {
    cd -- "$base_dir"
    wget --quiet -- "$boost_url"
    tar xzvf "$boost_fs.tar.gz" > /dev/null
}

build() {
    cd -- "$boost_dir"
    ./bootstrap.sh

    ./b2                                            \
        "address-model=$address_model"              \
        variant="$configuration"                    \
        "--stagedir=stage/$platform/$configuration" \
        "$@"
}

main() {
    download
    build "$@"
}

main "$@"
