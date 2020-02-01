# Travis/AppVeyor commands.
# Basically, make is used as a kinda-portable shell.

.DEFAULT_GOAL := all
.SUFFIXES:

windows := 0
ifeq ($(OS),Windows_NT)
windows := 1
endif

# Shell
ifeq ($(windows),1)
# Make might pick up sh.exe if it's available:
SHELL := cmd
else
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
endif

# Shut Boost.Build's executable up:
b2_flags = -d0

# Basic stuff that needed to be abstracted away:
ifeq ($(windows),1)
ext := .exe
newline := @echo.
cwd := $(shell cd)
ls := dir /a-D /S /B
else
ext :=
newline := @echo
cwd := $(shell pwd)
ls := ls --almost-all -R
endif

# Python executable might be named differently, depending on the environment:
ifeq ($(windows),1)
ifdef appveyor_python_exe
python := $(appveyor_python_exe)
else
python := python
endif
else
python := python3
endif

# The build scripts are not completely OS-agnostic, unfortunately:
ifeq ($(windows),1)
x64_args = -A x64
x86_args = -A Win32
install_prefix = C:/install
else
x64_args := -D "CMAKE_TOOLCHAIN_FILE=$$TRAVIS_BUILD_DIR/cmake/toolchains/gcc-x64.cmake"
x86_args := -D "CMAKE_TOOLCHAIN_FILE=$$TRAVIS_BUILD_DIR/cmake/toolchains/gcc-x86.cmake"
install_prefix := $$HOME/install
endif

# Script to verify executable's target architecture:
ifeq ($(windows),1)
verify_arch = powershell -file ./.ci/verify_arch.ps1
else
verify_arch := ./.ci/verify_arch.sh
endif

.PHONY: all
all: simple static dynamic

FORCE:

echo/%/build: FORCE
	$(newline)
	@echo =====================================================================
	@echo Building cmake/examples/$*
	@echo =====================================================================

echo/%/run: FORCE
	@echo ---------------------------------------------------------------------
	@echo Running $*/bin/foo
	@echo ---------------------------------------------------------------------

echo/%/verify: FORCE
	@echo ---------------------------------------------------------------------
	@echo Verifying $*/bin/foo
	@echo ---------------------------------------------------------------------

echo/%/finished: FORCE
	@echo =====================================================================
	$(newline)

# examples/simple: x64/Release build.

simple/build: echo/simple/build
	"$(python)" cmake/build/build.py --install "$(install_prefix)/simple" --configuration Release -- cmake/examples/simple $(x64_args)

simple/run: echo/simple/run
	"$(install_prefix)/simple/bin/foo"

simple/verify: echo/simple/verify
	$(verify_arch) "$(install_prefix)/simple/bin/foo$(ext)" x64

simple: simple/build simple/run simple/verify echo/simple/finished

.PHONY: simple simple/build simple/run simple/verify

# examples/static: x86/Debug build.

static/build: echo/static/build
	"$(python)" cmake/build/build.py --install "$(install_prefix)/static" --configuration Debug -- cmake/examples/static $(x86_args)

static/run: echo/static/run
	"$(install_prefix)/static/bin/foo"

static/verify: echo/static/verify
	$(verify_arch) "$(install_prefix)/static/bin/foo$(ext)" x86

static: static/build static/run static/verify echo/static/finished

.PHONY: static static/build static/run static/verify

# examples/dynamic: x64/RelWithDebInfo build.

dynamic/build: echo/dynamic/build
	"$(python)" cmake/build/build.py --install "$(install_prefix)/dynamic" --configuration RelWithDebInfo -- cmake/examples/dynamic $(x64_args)

# Windows can pick up DLLs in the same directory, otherwise we need to add them
# to PATH.
dynamic/run: echo/dynamic/run
ifeq ($(windows),1)
	"$(install_prefix)/dynamic/bin/foo"
else
	LD_LIBRARY_PATH="$(install_prefix)/dynamic/lib" "$(install_prefix)/dynamic/bin/foo"
endif

dynamic/verify: echo/dynamic/verify
	$(verify_arch) "$(install_prefix)/dynamic/bin/foo$(ext)" x64

dynamic: dynamic/build dynamic/run dynamic/verify echo/dynamic/finished

.PHONY: dynamic dynamic/build dynamic/run dynamic/verify

echo/boost/%/build: FORCE
	$(newline)
	@echo =====================================================================
	@echo Building Boost 1.$*.0
	@echo =====================================================================

echo/boost/%/ls: FORCE
	@echo ---------------------------------------------------------------------
	@echo Boost 1.$*.0: stage/
	@echo ---------------------------------------------------------------------

echo/boost/%/exe/build: FORCE
	@echo ---------------------------------------------------------------------
	@echo Boost 1.$*.0: building cmake/examples/boost
	@echo ---------------------------------------------------------------------

echo/boost/%/exe/run: FORCE
	@echo ---------------------------------------------------------------------
	@echo Boost 1.$*.0: running boost_1_$*_0/bin/foo
	@echo ---------------------------------------------------------------------

echo/boost/%/exe/verify: FORCE
	@echo ---------------------------------------------------------------------
	@echo Boost 1.$*.0: verifying boost_1_$*_0/bin/foo
	@echo ---------------------------------------------------------------------

echo/boost/%/finished: FORCE
	@echo =====================================================================
	$(newline)

# Boost 1.58.0:
# * temporary download,
# * x86, Debug, static libraries only.
# examples/boost:
# * x86/Debug build.

boost/58/download: echo/boost/58/build
	"$(python)" boost/build/build.py download 1.58.0

boost/58/build:
	"$(python)" boost/build/build.py build --configuration Debug --platform x86 --link static -- ./boost_1_58_0 --with-filesystem --with-program_options $(b2_flags)

boost/58/ls: echo/boost/58/ls
	$(ls) "./boost_1_58_0/stage"

boost/58/exe/build: echo/boost/58/exe/build
	"$(python)" cmake/build/build.py --install "$(install_prefix)/boost_1_58_0" --configuration Debug -- cmake/examples/boost $(x86_args) -D "BOOST_ROOT=$(cwd)/boost_1_58_0" -D "BOOST_LIBRARYDIR=$(cwd)/boost_1_58_0/stage/x86/Debug/lib"

# Boost should be linked statically, no need to adjust PATH:
boost/58/exe/run: echo/boost/58/exe/run
	"$(install_prefix)/boost_1_58_0/bin/foo"

boost/58/exe/verify: echo/boost/58/exe/verify
	$(verify_arch) "$(install_prefix)/boost_1_58_0/bin/foo$(ext)" x86

boost/58/exe: boost/58/exe/build boost/58/exe/run boost/58/exe/verify

boost/58: boost/58/download boost/58/build boost/58/ls boost/58/exe echo/boost/58/finished

.PHONY: boost/58 boost/58/download boost/58/build boost/58/ls boost/58/exe boost/58/exe/build boost/58/exe/run boost/58/exe/verify

# Boost 1.72.0:
# * cached download,
# * x86 & x64, Debug & Release, shared libraries only.
# examples/boost:
# * x64/Release build.

boost/72/download: echo/boost/72/build
	"$(python)" boost/build/build.py download --cache . 1.72.0

boost/72/build:
	"$(python)" boost/build/build.py build --platform x86 x64 --link shared -- ./boost_1_72_0 --with-filesystem --with-program_options $(b2_flags)

boost/72/ls: echo/boost/72/ls
	$(ls) "./boost_1_72_0/stage"

boost/72/exe/build: echo/boost/72/exe/build
	"$(python)" cmake/build/build.py --install "$(install_prefix)/boost_1_72_0" --configuration Release -- cmake/examples/boost $(x64_args) -D "BOOST_ROOT=$(cwd)/boost_1_72_0" -D "BOOST_LIBRARYDIR=$(cwd)/boost_1_72_0/stage/x64/Release/lib" -D Boost_USE_STATIC_LIBS=OFF

# Boost is linked dynamically, we need to adjust PATH:
boost/72/exe/run: echo/boost/72/exe/run
ifeq ($(windows),1)
	set "PATH=$(cwd)\boost_1_72_0\stage\x64\Release\lib;%PATH%" && "$(install_prefix)/boost_1_72_0/bin/foo"
else
	LD_LIBRARY_PATH="$(cwd)/boost_1_72_0/stage/x64/Release/lib" "$(install_prefix)/boost_1_72_0/bin/foo"
endif

boost/72/exe/verify: echo/boost/72/exe/verify
	$(verify_arch) "$(install_prefix)/boost_1_72_0/bin/foo$(ext)" x64

boost/72/exe: boost/72/exe/build boost/72/exe/run boost/72/exe/verify

boost/72: boost/72/download boost/72/build boost/72/ls boost/72/exe echo/boost/72/finished

.PHONY: boost/72 boost/72/download boost/72/build boost/72/ls boost/72/exe boost/72/exe/build boost/72/exe/run boost/72/exe/verify

# Boost 1.65.0:
# * download to $HOME (on Travis), C:\projects (on AppVeyor),
# * x64, MinSizeRel (= Release), static & shared libraries.
# examples/boost:
# * x64/MinSizeRel build (set in .travis.yml and .appveyor.yml).

ifdef TRAVIS
boost/65/build: echo/boost/65/build
	"$(python)" boost/build/ci/travis.py --link static -- --with-filesystem --with-program_options $(b2_flags)

boost/65/ls: echo/boost/65/ls
	$(ls) "$$HOME/boost/stage"

boost/65/exe/build: echo/boost/65/exe/build
	TRAVIS_BUILD_DIR="$$TRAVIS_BUILD_DIR/cmake/examples/boost" "$(python)" cmake/build/ci/travis.py --install "$(install_prefix)/boost_1_65_0" -- -D "BOOST_ROOT=$$HOME/boost" -D "BOOST_LIBRARYDIR=$$HOME/boost/stage/$$platform/$$configuration/lib"
endif
ifdef APPVEYOR
boost/65/build: echo/boost/65/build
	"$(python)" boost/build/ci/appveyor.py --link static -- --with-filesystem --with-program_options $(b2_flags)

boost/65/ls: echo/boost/65/ls
	$(ls) "C:/projects/boost/stage"

boost/65/exe/build: echo/boost/65/exe/build
	set "APPVEYOR_BUILD_FOLDER=%APPVEYOR_BUILD_FOLDER%\cmake\examples\boost" && "$(python)" cmake/build/ci/appveyor.py --install "$(install_prefix)/boost_1_65_0" -- -D "BOOST_ROOT=C:\projects\boost" -D "BOOST_LIBRARYDIR=C:\projects\boost\stage\%PLATFORM%\%CONFIGURATION%\lib"
endif

boost/65/exe/run: echo/boost/65/exe/run
	"$(install_prefix)/boost_1_65_0/bin/foo"

boost/65/exe/verify: echo/boost/65/exe/verify
	$(verify_arch) "$(install_prefix)/boost_1_65_0/bin/foo$(ext)" x64

boost/65/exe: boost/65/exe/build boost/65/exe/run boost/65/exe/verify

boost/65: boost/65/build boost/65/ls boost/65/exe echo/boost/65/finished

.PHONY: boost/65 boost/65/build boost/65/ls boost/65/exe boost/65/exe/build boost/65/exe/run boost/65/exe/verify
