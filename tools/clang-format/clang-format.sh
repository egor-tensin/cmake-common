#!/usr/bin/env bash

# Copyright (c) 2020 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

set -o errexit -o nounset -o pipefail

# Utility

script_name="$( basename -- "${BASH_SOURCE[0]}" )"
readonly script_name

dump() {
    local prefix="${FUNCNAME[0]}"
    [ "${#FUNCNAME[@]}" -gt 1 ] && prefix="${FUNCNAME[1]}"

    local msg
    for msg; do
        echo "$script_name: $prefix: $msg"
    done
}

# Settings

clang_format='clang-format'
clang_format_style='file'
clang_format_diff=

update_clang_format() {
    if [ "$#" -ne 1 ]; then
        echo "usage: ${FUNCNAME[0]} CLANG_FORMAT_PATH" >&2
        return 1
    fi

    local new_clang_format="$1"

    if ! command -v "$new_clang_format" > /dev/null 2>&1; then
        dump "couldn't find clang-format at: $new_clang_format" >&2
        return 1
    fi

    clang_format="$new_clang_format"
}

# Command line parsing

script_usage() {
    local msg
    for msg; do
        echo "$script_name: $msg"
    done

    echo "usage: $script_name [-h|--help] [-b|--clang-format PATH] [-s|--style STYLE] [--diff]
  -h,--help            show this message and exit
  -b,--clang-format    set path to clang-format executable
  -s,--style           clang-format -style parameter argument
  --diff               don't edit the files, just show the diff"
}

parse_script_options() {
    while [ "$#" -gt 0 ]; do
        local key="$1"
        shift

        case "$key" in
            -h|--help)
                script_usage
                exit 0
                ;;
            --diff)
                clang_format_diff=1
                continue
                ;;
            -b|--clang-format|-s|--style)
                ;;
            *)
                script_usage "unrecognized parameter: $key" >&2
                exit 1
                ;;
        esac

        if [ "$#" -eq 0 ]; then
            script_usage "missing argument for parameter: $key" >&2
            exit 1
        fi

        local value="$1"
        shift

        case "$key" in
            -b|--clang-format)
                update_clang_format "$value"
                ;;
            -s|--style)
                clang_format_style="$value"
                ;;
            *)
                script_usage "unrecognized parameter: $key" >&2
                exit 1
                ;;
        esac
    done
}

# Routines for running clang-format

run_clang_format_diff() {
    local exit_code=0
    local file

    for file; do
        if "$clang_format" "-style=$clang_format_style" -- "$file" | diff --unified --label="$file (original)" --label="$file (clang-format)" -- "$file" -; then
            continue
        else
            exit_code="$?"
            [ "$exit_code" -eq 1 ] && continue
            break
        fi
    done

    return "$exit_code"
}

run_clang_format_edit() {
    "$clang_format" -i "-style=$clang_format_style" -- "$@"
}

run_clang_format() {
    if [ -z "$clang_format_diff" ]; then
        run_clang_format_edit "$@"
    else
        run_clang_format_diff "$@"
    fi
}

# File traversal

list_all_files() {
    git ls-tree -r -z --name-only HEAD
}

declare -a cpp_extensions=(c h cc hh cpp hpp cxx hxx cp c++)

list_cpp_files() {
    local -A cpp_extension_set
    local ext

    for ext in ${cpp_extensions[@]+"${cpp_extensions[@]}"}; do
        cpp_extension_set[$ext]=1
    done

    local -a files=()
    local file

    while IFS= read -d '' -r file; do
        basename="$( basename -- "$file" )"
        ext="${basename##*.}"
        [ "$ext" = "$basename" ] && continue # No .EXTension

        [ -n "${cpp_extension_set[$ext]+x}" ] && files+=("$file")
    done < <( list_all_files )

    printf -- '%s\0' ${files[@]+"${files[@]}"}
}

# Main routines

process_cpp_files() {
    local -a files=()
    local file

    while IFS= read -d '' -r file; do
        files+=("$file")
    done < <( list_cpp_files )

    run_clang_format ${files[@]+"${files[@]}"}
}

main() {
    parse_script_options "$@"
    process_cpp_files
}

main "$@"
