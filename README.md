cmake-common
============

[![Basic usage](https://github.com/egor-tensin/cmake-common/workflows/Basic%20usage/badge.svg)](https://github.com/egor-tensin/cmake-common/actions?query=workflow%3A%22Basic+usage%22)
[![Boost (toolsets)](https://github.com/egor-tensin/cmake-common/workflows/Boost%20(toolsets)/badge.svg)](https://github.com/egor-tensin/cmake-common/actions?query=workflow%3A%22Boost+%28toolsets%29%22)
[![Examples (toolsets)](https://github.com/egor-tensin/cmake-common/workflows/Examples%20(toolsets)/badge.svg)](https://github.com/egor-tensin/cmake-common/actions?query=workflow%3A%22Examples+%28toolsets%29%22)

Various utilities to help develop C++/CMake projects.

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

All of those are verified continuously by the "Boost (toolsets)" and "Examples
(toolsets)" workflows.

Usage
-----

### common.cmake

Use in a project by putting

    include(path/to/common.cmake)

in CMakeLists.txt.

This file aids in quick-and-dirty development by

* linking everything (including the runtime) statically by default,
* setting some useful compilation options (enables warnings, defines useful
Windows-specific macros, strips debug symbols in release builds, etc.).

Everything is optional (use the `CC_*` CMake options to opt out).

### Boost

Download & build the Boost libraries in a cross-platform way.

    $ python3 -m project.boost.download 1.72.0
    ...

    $ python3 -m project.boost.build -- boost_1_72_0/ --with-filesystem --with-program_options
    ...

Pass the `--help` flag to view detailed usage information.

    $ python3 -m project.boost.download --help
    $ python3 -m project.boost.build --help

### CMake project

Build (and optionally, install) a CMake project.

    $ python3 -m project.cmake.build --configuration Release --install path/to/somewhere -- examples/simple
    ...

    $ ./path/to/somewhere/bin/foo
    foo

Pass the `--help` flag to view detailed usage information.

    $ python3 -m project.cmake.build --help

### CI

Utility modules `project.ci.boost` and `project.ci.cmake` allow building Boost
and CMake projects on multiple CI systems.
They work by calling the generic scripts from above, auto-filling some
parameters from environment variables.

|                   | Travis           | AppVeyor              | GitHub Actions
| ----------------- | ---------------- | --------------------- | ----------------------------
| `--platform`      | `$platform`      | `$PLATFORM`           | `$platform`
| `--configuration` | `$configuration` | `$CONFIGURATION`      | `$configuration`
| Boost version     | `$boost_version` | `$boost_version`      | `$boost_version`
| Boost path        | `$HOME/boost/`   | `C:\projects\boost`   | `$RUNNER_WORKSPACE/boost/`
| Build path        | `$HOME/build/`   | `C:\projects\build`   | `$RUNNER_WORKSPACE/build/`
| Install path      | `$HOME/install/` | `C:\projects\install` | `$RUNNER_WORKSPACE/install/`

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

before_script: python3 -m project.ci.boost -- --with-filesystem
script: python3 -m project.ci.cmake --install
```

is equivalent to running

```
python3 -m project.boost.download --unpack "$HOME" -- 1.65.0
mv -- "$HOME/boost_1_65_0" "$HOME/boost"

python3 -m project.boost.build \
    --platform x64             \
    --configuration Debug      \
    --                         \
    "$HOME/boost"              \
    --with-filesystem

python3 -m project.cmake.build \
    --platform x64             \
    --configuration Debug      \
    --boost "$HOME/boost"      \
    --build "$HOME/build"      \
    --install "$HOME/install"  \
    --                         \
    "$TRAVIS_BUILD_DIR"
```

twice (the `--configuration` parameter having the value of `Release` for the
second run).

### clang-format.py

`clang-format` all C/C++ files in a project.

    $ cd project/
    $ python3 path/to/tools/clang-format.py      # Prints a diff
    $ python3 path/to/tools/clang-format.py -i   # Edits files in-place

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
