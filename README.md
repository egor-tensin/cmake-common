cmake-common
============

[![Basic usage](https://github.com/egor-tensin/cmake-common/actions/workflows/basic.yml/badge.svg)](https://github.com/egor-tensin/cmake-common/actions/workflows/basic.yml)
[![Boost (toolsets)](https://github.com/egor-tensin/cmake-common/actions/workflows/boost_toolsets.yml/badge.svg)](https://github.com/egor-tensin/cmake-common/actions/workflows/boost_toolsets.yml)
[![Examples (toolsets)](https://github.com/egor-tensin/cmake-common/actions/workflows/example_toolsets.yml/badge.svg)](https://github.com/egor-tensin/cmake-common/actions/workflows/example_toolsets.yml)

Various utilities to help develop C++/CMake projects.

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
  | cmake-build    | `python3 -m project.cmake.build`
  | ci-boost       | `python3 -m project.ci.boost`
  | ci-cmake       | `python3 -m project.ci.cmake`

Toolchains
----------

Supported platform/build system/compiler combinations include, but are not
limited to:

| Platform | Build system | Compiler
| -------- | ------------ | --------
| Linux    | make         | Clang
|          |              | GCC
|          |              | MinGW-w64
| Windows  | make \[1\]   | Clang (clang/clang++)
|          |              | Clang (clang-cl \[2\])
|          |              | MinGW-w64
|          | msbuild      | MSVC
| Cygwin   | make         | Clang
|          |              | GCC
|          |              | MinGW-w64

1. Both GNU `make` and MinGW `mingw32-make`.
2. Boost 1.69.0 or higher only.

All of those are verified continuously by the [Boost (toolsets)] and [Examples
(toolsets)] workflows.

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

    $ cmake-build --configuration Release --install path/to/somewhere --boost path/to/boost -- examples/simple
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
* setting some useful compilation options (enables warnings, defines useful
Windows-specific macros, strips debug symbols in release builds, etc.).

Everything is optional (use the `CC_*` CMake options to opt out).

### CI

Utility scripts `ci-boost` and `ci-cmake` allow building Boost and CMake
projects on multiple CI systems.
They work by calling the generic scripts from above, auto-filling some
parameters from environment variables.

|                   | Travis                               | AppVeyor                                   | GitHub Actions
| ----------------- | ------------------------------------ | ------------------------------------------ | --------------
| `--toolset`       | `$TOOLSET`                           | `%TOOLSET%`                                | `$TOOLSET`
| `--platform`      | `$PLATFORM`                          | `%PLATFORM%`                               | `$PLATFORM`
| `--configuration` | `$CONFIGURATION`                     | `%CONFIGURATION%`                          | `$CONFIGURATION`
| Boost version     | `$BOOST_VERSION`                     | `%BOOST_VERSION%`                          | `$BOOST_VERSION`
| Boost path        | `$TRAVIS_BUILD_DIR/../build/boost`   | `%APPVEYOR_BUILD_FOLDER%\..\build\boost`   | `$GITHUB_WORKSPACE/../build/boost`
| Build path        | `$TRAVIS_BUILD_DIR/../build/cmake`   | `%APPVEYOR_BUILD_FOLDER%\..\build\cmake`   | `$GITHUB_WORKSPACE/../build/cmake`
| Install path      | `$TRAVIS_BUILD_DIR/../build/install` | `%APPVEYOR_BUILD_FOLDER%\..\build\install` | `$GITHUB_WORKSPACE/../build/install`

For example, the following Travis workflow:

```
language: cpp
os: linux
dist: focal

env:
  global:
    boost_version: 1.65.0
  jobs:
    - configuration=Debug   platform=x64
    - configuration=Release platform=x64

before_script: ci-boost -- --with-filesystem
script: ci-cmake --install
```

is roughly equivalent to running

```
boost-download --cache "$TRAVIS_BUILD_DIR/../build" -- 1.65.0
mv -- \
    "$TRAVIS_BUILD_DIR/../build/boost_1_65_0" \
    "$TRAVIS_BUILD_DIR/../build/boost"

boost-build                            \
    --platform x64                     \
    --configuration Debug Release      \
    --                                 \
    "$TRAVIS_BUILD_DIR/../build/boost" \
    --with-filesystem

for configuration in Debug Release; do
    cmake-build                                        \
        --platform x64                                 \
        --configuration "$configuration"               \
        --boost "$TRAVIS_BUILD_DIR/../build/boost"     \
        --build "$TRAVIS_BUILD_DIR/../build/cmake"     \
        --install "$TRAVIS_BUILD_DIR/../build/install" \
        --                                             \
        "$TRAVIS_BUILD_DIR"
done
```

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

License
-------

Distributed under the MIT License.
See [LICENSE.txt] for details.

[LICENSE.txt]: LICENSE.txt
