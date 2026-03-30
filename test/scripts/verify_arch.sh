#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_name="$( basename -- "${BASH_SOURCE[0]}" )"
readonly script_name

elf_file_class() {
    local path
    for path; do
        od --address-radix=n --skip-bytes=4 --read-bytes=1 --format=x1 -- "$path"
    done
}

arch_to_file_class() {
    local arch
    for arch; do
        case "$arch" in
            x86)
                echo '01'
                ;;
            x64)
                echo '02'
                ;;
            *)
                echo "$script_name: unsupported architecture: $arch" >&2
                return 1
                ;;
        esac
    done
}

main() {
    if [ "$#" -ne 2 ]; then
        echo "usage: $script_name BIN_PATH ARCH" >&2
        return 1
    fi

    local path="$1"
    local arch="$2"

    local expected
    expected=" $( arch_to_file_class "$arch" )"
    local actual
    actual="$( elf_file_class "$path" )"

    if [ "$expected" = "$actual" ]; then
        echo "$script_name: file '$path' matches architecture '$arch'"
    else
        echo "$script_name: file '$path' DOES NOT match architecture '$arch'"
        echo "$script_name: expected ELF file class '$expected', actual file class is '$actual'" >&2
        return 1
    fi
}

main "$@"
