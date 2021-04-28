`ci-boost` and `ci-cmake` are thin wrappers around `boost-download`/`boost-build`
and `cmake-build` accordingly.  They work by reading environment variables and
passing their values as command line parameters to the more generic scripts.
This facilitates matrix-building the project without too much fuss.

For example, the following Travis workflow:

```
language: cpp
os: linux
dist: focal

env:
  global:
    BOOST_VERSION: 1.65.0
  jobs:
    - CONFIGURATION=Debug   PLATFORM=x64
    - CONFIGURATION=Release PLATFORM=x64

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

Caching
-------

`ci-boost` downloads the Boost distribution archive to the "../build/"
directory (resolved relatively to the root checkout directory).  You can cache
the archive like this (using GitHub Actions as an example):

```
- name: Cache Boost
  uses: actions/cache@v2
  with:
    path: '${{ runner.workspace }}/build/boost_*.tar.gz'
    key: 'boost_${{ env.BOOST_VERSION }}'

- name: Build Boost
  # This won't re-download the archive unnecessarily.
  run: ci-boost -- --with-filesystem
```
