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
.SHELLFLAGS := /c
else
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
endif

makefile_dir := $(dir $(realpath $(firstword $(MAKEFILE_LIST))))

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
ls := function my_ls() { find "$$@" -type f | sort ; } ; my_ls
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

ifeq ($(windows),1)
install_prefix = C:/install
else
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

.PHONY: FORCE
FORCE:

echo/%/build: FORCE
	$(newline)
	@echo =====================================================================
	@echo Building examples/$*
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

.PHONY: simple/build
simple/build: echo/simple/build
	"$(python)" -m project.cmake.build --install "$(install_prefix)/simple" --platform x64 --configuration Release examples/simple

.PHONY: simple/run
simple/run: echo/simple/run
	"$(install_prefix)/simple/bin/foo"

.PHONY: simple/verify
simple/verify: echo/simple/verify
	$(verify_arch) "$(install_prefix)/simple/bin/foo$(ext)" x64

.PHONY: simple
simple: simple/build simple/run simple/verify echo/simple/finished

# examples/static: x86/Debug build.

.PHONY: static/build
static/build: echo/static/build
	"$(python)" -m project.cmake.build --install "$(install_prefix)/static" --platform x86 --configuration Debug examples/static

.PHONY: static/run
static/run: echo/static/run
	"$(install_prefix)/static/bin/foo"

.PHONY: static/verify
static/verify: echo/static/verify
	$(verify_arch) "$(install_prefix)/static/bin/foo$(ext)" x86

.PHONY: static
static: static/build static/run static/verify echo/static/finished

# examples/dynamic: x64/RelWithDebInfo build.

.PHONY: dynamic/build
dynamic/build: echo/dynamic/build
	"$(python)" -m project.cmake.build --install "$(install_prefix)/dynamic" --platform x64 --configuration RelWithDebInfo examples/dynamic

.PHONY: dynamic/run
# Windows can pick up DLLs in the same directory, otherwise we need to add them
# to PATH.
dynamic/run: echo/dynamic/run
ifeq ($(windows),1)
	"$(install_prefix)/dynamic/bin/foo"
else
	LD_LIBRARY_PATH="$(install_prefix)/dynamic/lib" "$(install_prefix)/dynamic/bin/foo"
endif

.PHONY: dynamic/verify
dynamic/verify: echo/dynamic/verify
	$(verify_arch) "$(install_prefix)/dynamic/bin/foo$(ext)" x64

.PHONY: dynamic
dynamic: dynamic/build dynamic/run dynamic/verify echo/dynamic/finished

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
	@echo Boost 1.$*.0: building examples/boost
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

.PHONY: boost/58/download
boost/58/download: echo/boost/58/build
	"$(python)" -m project.boost.download 1.58.0

.PHONY: boost/58/build
boost/58/build:
	"$(python)" -m project.boost.build --configuration Debug --platform x86 --link static -- ./boost_1_58_0 --with-filesystem --with-program_options

.PHONY: boost/58/ls
boost/58/ls: echo/boost/58/ls
	$(ls) "./boost_1_58_0/stage"

.PHONY: boost/58/exe/build
boost/58/exe/build: echo/boost/58/exe/build
	"$(python)" -m project.cmake.build --install "$(install_prefix)/boost_1_58_0" --platform x86 --configuration Debug --boost boost_1_58_0 examples/boost

.PHONY: boost/58/exe/run
# Boost should be linked statically, no need to adjust PATH:
boost/58/exe/run: echo/boost/58/exe/run
	"$(install_prefix)/boost_1_58_0/bin/foo"

.PHONY: boost/58/exe/verify
boost/58/exe/verify: echo/boost/58/exe/verify
	$(verify_arch) "$(install_prefix)/boost_1_58_0/bin/foo$(ext)" x86

.PHONY: boost/58/exe
boost/58/exe: boost/58/exe/build boost/58/exe/run boost/58/exe/verify

.PHONY: boost/58
boost/58: boost/58/download boost/58/build boost/58/ls boost/58/exe echo/boost/58/finished

# Boost 1.72.0:
# * cached download,
# * x86 & x64, Debug & Release, shared libraries only.
# examples/boost:
# * x64/Release build.

.PHONY: boost/72/download
boost/72/download: echo/boost/72/build
	"$(python)" -m project.boost.download --cache . 1.72.0

.PHONY: boost/72/build
boost/72/build:
	"$(python)" -m project.boost.build --platform x86 x64 --link shared -- ./boost_1_72_0 --with-filesystem --with-program_options

.PHONY: boost/72/ls
boost/72/ls: echo/boost/72/ls
	$(ls) "./boost_1_72_0/stage"

.PHONY: boost/72/exe/build
boost/72/exe/build: echo/boost/72/exe/build
	"$(python)" -m project.cmake.build --install "$(install_prefix)/boost_1_72_0" --platform x64 --configuration Release --boost boost_1_72_0 -- examples/boost -D Boost_USE_STATIC_LIBS=OFF

.PHONY: boost/72/exe/run
# Boost is linked dynamically, we need to adjust PATH:
boost/72/exe/run: echo/boost/72/exe/run
ifeq ($(windows),1)
	set "PATH=$(cwd)\boost_1_72_0\stage\x64\Release\lib;%PATH%" && "$(install_prefix)/boost_1_72_0/bin/foo"
else
	LD_LIBRARY_PATH="$(cwd)/boost_1_72_0/stage/x64/Release/lib" "$(install_prefix)/boost_1_72_0/bin/foo"
endif

.PHONY: boost/72/exe/verify
boost/72/exe/verify: echo/boost/72/exe/verify
	$(verify_arch) "$(install_prefix)/boost_1_72_0/bin/foo$(ext)" x64

.PHONY: boost/72/exe
boost/72/exe: boost/72/exe/build boost/72/exe/run boost/72/exe/verify

.PHONY: boost/72
boost/72: boost/72/download boost/72/build boost/72/ls boost/72/exe echo/boost/72/finished

# Boost 1.65.0:
# * download to $HOME (on Travis), C:\projects (on AppVeyor),
# * x64, MinSizeRel (= Release), static & shared libraries.
# examples/boost:
# * x64/MinSizeRel build (set in .travis.yml and .appveyor.yml).

ifdef TRAVIS
.PHONY: boost/65/build
boost/65/build: echo/boost/65/build
	"$(python)" -m project.ci.travis.boost --link static -- --with-filesystem --with-program_options

.PHONY: boost/65/ls
boost/65/ls: echo/boost/65/ls
	$(ls) "$$HOME/boost/stage"

.PHONY: boost/65/exe/build
boost/65/exe/build: echo/boost/65/exe/build
	TRAVIS_BUILD_DIR="$$TRAVIS_BUILD_DIR/examples/boost" "$(python)" -m project.ci.travis.cmake --install "$(install_prefix)/boost_1_65_0"
endif
ifdef APPVEYOR
.PHONY: boost/65/build
boost/65/build: echo/boost/65/build
	"$(python)" -m project.ci.appveyor.boost --link static -- --with-filesystem --with-program_options

.PHONY: boost/65/ls
boost/65/ls: echo/boost/65/ls
	$(ls) "C:/projects/boost/stage"

.PHONY: boost/65/exe/build
boost/65/exe/build: echo/boost/65/exe/build
	set "APPVEYOR_BUILD_FOLDER=%APPVEYOR_BUILD_FOLDER%\examples\boost" && "$(python)" -m project.ci.appveyor.cmake --install "$(install_prefix)/boost_1_65_0"
endif

.PHONY: boost/65/exe/run
boost/65/exe/run: echo/boost/65/exe/run
	"$(install_prefix)/boost_1_65_0/bin/foo"

.PHONY: boost/65/exe/verify
boost/65/exe/verify: echo/boost/65/exe/verify
	$(verify_arch) "$(install_prefix)/boost_1_65_0/bin/foo$(ext)" x64

.PHONY: boost/65/exe
boost/65/exe: boost/65/exe/build boost/65/exe/run boost/65/exe/verify

.PHONY: boost/65
boost/65: boost/65/build boost/65/ls boost/65/exe echo/boost/65/finished
