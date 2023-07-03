cmake-common
============

[![Basic usage](https://github.com/egor-tensin/cmake-common/actions/workflows/basic.yml/badge.svg)](https://github.com/egor-tensin/cmake-common/actions/workflows/basic.yml)
[![Boost (toolsets)](https://github.com/egor-tensin/cmake-common/actions/workflows/boost_toolsets.yml/badge.svg)](https://github.com/egor-tensin/cmake-common/actions/workflows/boost_toolsets.yml)
[![Examples (toolsets)](https://github.com/egor-tensin/cmake-common/actions/workflows/example_toolsets.yml/badge.svg)](https://github.com/egor-tensin/cmake-common/actions/workflows/example_toolsets.yml)

Utilities to help develop C++/CMake projects.

Description
-----------

This main goal of this project is to make it easier to build (potentially,
cross-compile) Boost and CMake projects using different toolsets.
It does so providing a set of command-line utilities that allow users to
download/build Boost & use it in a CMake project in a consistent way &mdash; no
matter the compiler or the target platform.

Installation
------------

* Via PyPI:

      pip install cmake-common

* As a submodule:

      git submodule add https://github.com/egor-tensin/cmake-common.git

  All the scripts provided by the PyPI package are thin wrappers around the
  `project` package modules:

  | Script         | Module
  | -------------- | ------
  | boost-download | `python3 -m project.boost.download`
  | boost-build    | `python3 -m project.boost.build`
  | project-build  | `python3 -m project.build`

Toolsets
--------

Supported platform/build system/compiler combinations include, but are not
limited to:

| Platform | Build system   | Compiler    |
| -------- | -------------- | ----------- |
| Linux    | make           | Clang       |
|          |                | GCC         |
|          |                | MinGW-w64   |
| Windows  | make \[1\]     | Clang \[2\] |
|          |                | MinGW-w64   |
|          | msbuild        | MSVC        |
| Cygwin   | make           | Clang       |
|          |                | GCC         |
|          |                | MinGW-w64   |

1. Both GNU make and MinGW mingw32-make.
2. clang-cl is supported by Boost 1.69.0 or higher only.

All of those are verified continuously by the [Boost (toolsets)] and [Examples
(toolsets)] workflows.

For a complete list of possible `--toolset` parameter values, pass the
`--help-toolsets` flag to either `boost-build` or `project-build`.

[Boost (toolsets)]: https://github.com/egor-tensin/cmake-common/actions/workflows/boost_toolsets.yml
[Examples (toolsets)]: https://github.com/egor-tensin/cmake-common/actions/workflows/example_toolsets.yml

Usage
-----

### Boost

Download & build the Boost libraries in a cross-platform way.

    $ boost-download 1.72.0
    ...

    $ boost-build -- boost_1_72_0/ --with-filesystem --with-program_options
    ...

Pass the `--help` flag to view detailed usage information.

### CMake project

Build (and optionally, install) a CMake project.

    $ project-build --configuration Release --install path/to/somewhere --boost path/to/boost -- examples/simple build/
    ...

    $ ./path/to/somewhere/bin/foo
    foo

Pass the `--help` flag to view detailed usage information.

### common.cmake

Use in a project by putting

    include(path/to/common.cmake)

in CMakeLists.txt.

This file aids in quick-and-dirty development by

* linking everything (including the runtime) statically by default,
* setting some useful compilation options (enables warnings, defines common
Windows-specific macros, strips debug symbols in release builds, etc.).

Everything is enabled by default (use the `CC_*` CMake options to opt out).

Tools
-----

* [project-clang-format.py] &mdash; `clang-format` all C/C++ files in the
project.
* [ctest-driver.py] &mdash; wrap an executable for testing with CTest;
cross-platform `grep`.

[project-clang-format.py]: docs/project-clang-format.md
[ctest-driver.py]: docs/ctest-driver.md

Examples
--------

I use this in all of my C++/CMake projects, e.g. [aes-tools] and [math-server].

[aes-tools]: https://github.com/egor-tensin/aes-tools
[math-server]: https://github.com/egor-tensin/math-server

Development
-----------

Make a git tag:

    git tag "v$( python -m setuptools_scm --strip-dev )"

You can then review that the tag is fine and push w/ `git push --tags`.

License
-------

Distributed under the MIT License.
See [LICENSE.txt] for details.

[LICENSE.txt]: LICENSE.txt
