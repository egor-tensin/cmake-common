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
readonly script_name="$( basename -- "${BASH_SOURCE[0]}" )"

dump() {
    local msg
    for msg; do
        echo "$script_name: $msg"
    done
}

set_paths() {
    local boost_fs="boost_${travis_boost_version//\./_}"

    readonly boost_archive="$boost_fs.tar.gz"
    readonly boost_url="https://dl.bintray.com/boostorg/release/$travis_boost_version/source/$boost_archive"
    readonly boost_dir="$base_dir/$boost_fs"
}

set_address_model() {
    if [ "$platform" = x64 ]; then
        readonly address_model=64
    elif [ "$platform" = x86 ]; then
        readonly address_model=32
    else
        dump "unsupported platform: $platform" >&2
        exit 1
    fi
}

set_configuration() {
    configuration="${configuration,,}"
    readonly configuration
}

set_parameters() {
    set_paths
    set_address_model
    set_configuration
}

download() {
    wget --quiet -O "$boost_archive" -- "$boost_url"
    tar xzvf "$boost_archive" > /dev/null
}

build() {
    cd -- "$boost_dir"

    ./bootstrap.sh

    ./b2                               \
        "address-model=$address_model" \
        variant="$configuration"       \
        "--stagedir=$boost_dir/stage/$platform/$configuration" \
        "$@"
}

main() {
    pushd -- "$base_dir"
    trap 'popd' EXIT
    set_parameters
    download
    build "$@"
}

main "$@"
