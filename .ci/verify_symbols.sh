#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

script_name="$( basename -- "${BASH_SOURCE[0]}" )"
readonly script_name

main() {
    if [ "$#" -lt 1 ]; then
        echo "usage: $script_name BIN_PATH [SYMBOL...]" >&2
        return 1
    fi

    local path="$1"
    shift

    local nm
    nm="$( nm --demangle -- "$path" 2>&1 )"

    if [ "$#" -eq 0 ]; then
        if [ "$nm" == "nm: $path: no symbols" ]; then
            echo "$script_name: file '$path' has no symbols, as expected"
            return 0
        else
            echo "$script_name: file '$path' should not have symbols, but it does" >&2
            return 1
        fi
    fi

    local symbol
    for symbol; do
        if echo "$nm" | grep -F -e " $symbol"; then
            echo "$script_name: file '$path' has symbol '$symbol'"
        else
            echo "$script_name: symbol '$symbol' wasn't found in file '$path'"
            echo "$script_name: here's the complete symbol list:"
            echo "$nm"
            return 1
        fi
    done
}

main "$@"
