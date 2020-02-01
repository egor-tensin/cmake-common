# Travis/AppVeyor commands.

boost_quiet = -d0

ifeq ($(OS),Windows_NT)
windows = 1
else
windows = 0
endif

ifeq ($(windows),1)
SHELL = cmd
ext = .exe
x64_args = -A x64
x86_args = -A Win32
install_prefix = C:/install
verify_arch = powershell -file ./.ci/verify_arch.ps1
python = python
ls = dir /a-D /S /B
cwd = $(shell cd)
else
ext =
x64_args =
x86_args = -D "CMAKE_TOOLCHAIN_FILE=$(TRAVIS_BUILD_DIR)/cmake/toolchains/gcc-x86.cmake"
install_prefix = $(HOME)/install
verify_arch = ./.ci/verify_arch.sh
python = python3
ls = ls --almost-all -R
cwd = $(shell pwd)
endif

ifdef appveyor_python_exe
python = $(appveyor_python_exe)
endif

# examples/simple: x64/Release build.

simple/build:
	"$(python)" cmake/build/build.py --install "$(install_prefix)/simple" --configuration Release -- cmake/examples/simple $(x64_args)

simple/run:
	"$(install_prefix)/simple/bin/foo"

simple/verify:
	$(verify_arch) "$(install_prefix)/simple/bin/foo$(ext)" x64

simple: simple/build simple/run simple/verify

.PHONY: simple simple/build simple/run simple/verify

# examples/static: x86/Debug build.

static/build:
	"$(python)" cmake/build/build.py --install "$(install_prefix)/static" --configuration Debug -- cmake/examples/static $(x86_args)

static/run:
	"$(install_prefix)/static/bin/foo"

static/verify:
	$(verify_arch) "$(install_prefix)/static/bin/foo$(ext)" x86

static: static/build static/run static/verify

.PHONY: static static/build static/run static/verify

# examples/dynamic: x64/RelWithDebInfo build.

dynamic/build:
	"$(python)" cmake/build/build.py --install "$(install_prefix)/dynamic" --configuration RelWithDebInfo -- cmake/examples/dynamic $(x64_args)

# Windows can pick up DLLs in the same directory, otherwise we need to add them
# to PATH.
dynamic/run:
ifeq ($(windows),1)
	"$(install_prefix)/dynamic/bin/foo"
else
	LD_LIBRARY_PATH="$(install_prefix)/dynamic/lib" "$(install_prefix)/dynamic/bin/foo"
endif

dynamic/verify:
	$(verify_arch) "$(install_prefix)/dynamic/bin/foo$(ext)" x64

dynamic: dynamic/build dynamic/run dynamic/verify

.PHONY: dynamic dynamic/build dynamic/run dynamic/verify

# Boost 1.58.0:
# * temporary download,
# * x86, Debug, static libraries only.
# examples/boost:
# * x86/Debug build.

boost/58/download:
	"$(python)" boost/build/build.py download 1.58.0

boost/58/build:
	"$(python)" boost/build/build.py build --configuration Debug --platform x86 --link static -- ./boost_1_58_0 --with-filesystem --with-program_options $(boost_quiet)

boost/58/ls:
	$(ls) "./boost_1_58_0/stage"

boost/58/exe/build:
	"$(python)" cmake/build/build.py --install "$(install_prefix)/boost_1_58_0" --configuration Debug -- cmake/examples/boost $(x86_args) -D "BOOST_ROOT=$(cwd)/boost_1_58_0" -D "BOOST_LIBRARYDIR=$(cwd)/boost_1_58_0/stage/x86/Debug/lib"

# Boost should be linked statically, no need to adjust PATH:
boost/58/exe/run:
	"$(install_prefix)/boost_1_58_0/bin/foo"

boost/58/exe/verify:
	$(verify_arch) "$(install_prefix)/boost_1_58_0/bin/foo$(ext)" x86

boost/58/exe: boost/58/exe/build boost/58/exe/run boost/58/exe/verify

boost/58: boost/58/download boost/58/build boost/58/ls boost/58/exe

.PHONY: boost/58 boost/58/download boost/58/build boost/58/ls boost/58/exe boost/58/exe/build boost/58/exe/run boost/58/exe/verify

# Boost 1.72.0:
# * cached download,
# * x86 & x64, Debug & Release, shared libraries only.
# examples/boost:
# * x64/Release build.

boost/72/download:
	"$(python)" boost/build/build.py download --cache . 1.72.0

boost/72/build:
	"$(python)" boost/build/build.py build --platform x86 x64 --link shared -- ./boost_1_72_0 --with-filesystem --with-program_options $(boost_quiet)

boost/72/ls:
	$(ls) "./boost_1_72_0/stage"

boost/72/exe/build:
	"$(python)" cmake/build/build.py --install "$(install_prefix)/boost_1_72_0" --configuration Release -- cmake/examples/boost $(x64_args) -D "BOOST_ROOT=$(cwd)/boost_1_72_0" -D "BOOST_LIBRARYDIR=$(cwd)/boost_1_72_0/stage/x64/Release/lib" -D Boost_USE_STATIC_LIBS=OFF

# Boost is linked dynamically, we need to adjust PATH:
boost/72/exe/run:
ifeq ($(windows),1)
	set "PATH=$(cwd)\boost_1_72_0\stage\x64\Release\lib;%PATH%" && "$(install_prefix)/boost_1_72_0/bin/foo"
else
	LD_LIBRARY_PATH="$(cwd)/boost_1_72_0/stage/x64/Release/lib" "$(install_prefix)/boost_1_72_0/bin/foo"
endif

boost/72/exe/verify:
	$(verify_arch) "$(install_prefix)/boost_1_72_0/bin/foo$(ext)" x64

boost/72/exe: boost/72/exe/build boost/72/exe/run boost/72/exe/verify

boost/72: boost/72/download boost/72/build boost/72/ls boost/72/exe

.PHONY: boost/72 boost/72/download boost/72/build boost/72/ls boost/72/exe boost/72/exe/build boost/72/exe/run boost/72/exe/verify

# Boost 1.65.0:
# * download to $HOME (on Travis), C:\ (on AppVeyor),
# x64, Release, static & shared libraries.
# examples/boost:
# * x64/MinSizeRel build (set in .travis.yml and .appveyor.yml).

ifdef TRAVIS
boost/65/build:
	"$(python)" boost/build/ci/travis.py --link static -- --with-filesystem --with-program_options $(boost_quiet)

boost/65/ls:
	$(ls) "$$HOME/boost/stage"

boost/65/exe/build:
	TRAVIS_BUILD_DIR="$$TRAVIS_BUILD_DIR/cmake/examples/boost" "$(python)" cmake/build/ci/travis.py --install "$(install_prefix)/boost_1_65_0" -- -D "BOOST_ROOT=$$HOME/boost" -D "BOOST_LIBRARYDIR=$$HOME/boost/stage/$$platform/$$configuration/lib"
endif
ifdef APPVEYOR
boost/65/build:
	"$(python)" boost/build/ci/appveyor.py --link static -- --with-filesystem --with-program_options $(boost_quiet)

boost/65/ls:
	$(ls) "C:/projects/boost/stage"

boost/65/exe/build:
	set "APPVEYOR_BUILD_FOLDER=%APPVEYOR_BUILD_FOLDER%\cmake\examples\boost" && "$(python)" cmake/build/ci/appveyor.py --install "$(install_prefix)/boost_1_65_0" -- -D "BOOST_ROOT=C:\projects\boost" -D "BOOST_LIBRARYDIR=C:\projects\boost\stage\%platform%\%configuration%\lib"
endif

boost/65/exe/run:
	"$(install_prefix)/boost_1_65_0/bin/foo"

boost/65/exe/verify:
	$(verify_arch) "$(install_prefix)/boost_1_65_0/bin/foo$(ext)" x64

boost/65/exe: boost/65/exe/build boost/65/exe/run boost/65/exe/verify

boost/65: boost/65/build boost/65/ls boost/65/exe
