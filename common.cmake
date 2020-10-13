# Copyright (c) 2017 Egor Tensin <Egor.Tensin@gmail.com>
# This file is part of the "cmake-common" project.
# For details, see https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# It's a CMake code snippet I use in all of my CMake projects.
# It makes targets link the runtime statically by default, strips debug symbols
# in release builds and sets a couple of useful compilation options.

# Add this to the top-level CMakeLists.txt (unless a higher version has already
# been specified):
#
#     cmake_minimum_required(VERSION 3.1)

# Without this policy set, this line:
#
#     if(toolset STREQUAL "MSVC")
#
# evaluates to false even when using Visual Studio (since MSVC is a predefined
# variable; it's completely bonkers).
if(NOT POLICY CMP0054)
    message(FATAL_ERROR "common.cmake uses CMP0054, which is unsupported by this CMake version")
endif()
cmake_policy(SET CMP0054 NEW)

# Toolset identification:

if(CMAKE_C_COMPILER_ID)
    set(toolset "${CMAKE_C_COMPILER_ID}")
elseif(CMAKE_CXX_COMPILER_ID)
    set(toolset "${CMAKE_CXX_COMPILER_ID}")
else()
    set(toolset "unknown")
endif()

if(toolset STREQUAL "GNU")
    set(is_gcc ON)
elseif(toolset STREQUAL "MSVC")
    set(is_msvc ON)
else()
    message(WARNING "Unrecognized toolset: ${toolset}")
endif()

# User-defined switches:

set(default_value ON)
get_directory_property(parent_dir PARENT_DIRECTORY)
if(parent_dir)
    set(default_value OFF)
endif()

if(NOT DEFINED CC_CXX_STANDARD)
    set(CC_CXX_STANDARD "14" CACHE STRING "C++ standard version")
endif()
if(NOT DEFINED CC_BEST_PRACTICES)
    option(CC_BEST_PRACTICES "Set common compiler options" "${default_value}")
endif()
if(NOT DEFINED CC_WINDOWS_DEF)
    option(CC_WINDOWS_DEF "Define useful Windows macros" "${default_value}")
endif()
if(NOT DEFINED CC_STATIC_RUNTIME)
    set(static_runtime_default_value "${default_value}")
    if(DEFINED Boost_USE_STATIC_LIBS AND NOT Boost_USE_STATIC_LIBS)
        # Linking to dynamic Boost libs and the static runtime is a no-no:
        set(static_runtime_default_value OFF)
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows" OR MINGW)
    else()
        # At this point, Linux-like environment & the GNU C Library are assumed.
        set(static_runtime_default_value OFF)
    endif()
    option(CC_STATIC_RUNTIME "Link the runtime statically" "${static_runtime_default_value}")
endif()
if(NOT DEFINED CC_STRIP_SYMBOLS)
    option(CC_STRIP_SYMBOLS  "Strip debug symbols" "${default_value}")
endif()

option(Boost_USE_STATIC_LIBS "Use the static Boost libraries" "${default_value}")
option(Boost_USE_STATIC_RUNTIME "Use Boost libraries linked to the runtime statically" "${CC_STATIC_RUNTIME}")

if(NOT parent_dir)
    message(STATUS "Toolset:                        ${toolset}")
    message(STATUS "C++ standard:                   ${CC_CXX_STANDARD}")
    message(STATUS "Set common compiler options:    ${CC_BEST_PRACTICES}")
    message(STATUS "Define useful Windows macros:   ${CC_WINDOWS_DEF}")
    message(STATUS "Use the static Boost libraries: ${Boost_USE_STATIC_LIBS}")
    message(STATUS "Link the runtime statically:    ${CC_STATIC_RUNTIME}")
    message(STATUS "Strip symbols:                  ${CC_STRIP_SYMBOLS}")
endif()

# C++ standard version:

set(CMAKE_CXX_STANDARD "${CC_CXX_STANDARD}")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Common compiler options routines:

function(_cc_best_practices_msvc target)
    set(compile_options /MP /W4)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        target_compile_options("${target}" PRIVATE ${compile_options})
    endif()
endfunction()

function(_cc_best_practices_gcc target)
    set(compile_options -Wall -Wextra)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        target_compile_options("${target}" PRIVATE ${compile_options})
    endif()
endfunction()

function(_cc_best_practices target)
    if(is_msvc)
        _cc_best_practices_msvc("${target}")
    elseif(is_gcc)
        _cc_best_practices_gcc("${target}")
    endif()
endfunction()

# Useful Windows macros routines:

function(_cc_common_windows_definitions target)
    set(compile_definitions WIN32_LEAN_AND_MEAN NOMINMAX)
    get_target_property(target_type "${target}" TYPE)
    if(target_type STREQUAL "INTERFACE_LIBRARY")
        target_compile_definitions("${target}" INTERFACE ${compile_definitions})
    else()
        get_target_property(aliased "${target}" ALIASED_TARGET)
        if(NOT aliased)
            target_compile_definitions("${target}" PRIVATE ${compile_definitions})
        endif()
    endif()
endfunction()

# Static runtime routines:

function(_cc_static_runtime_msvc target)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        target_compile_options("${target}" PRIVATE
            $<$<CONFIG:Debug>:/MTd>
            $<$<NOT:$<CONFIG:Debug>>:/MT>)
    endif()
endfunction()

function(_cc_static_runtime_gcc target)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        # This causes issues with mixing keyword- and plain- versions of
        # target_link_libraries:
        #target_link_libraries("${target}" PRIVATE -static)

        set_property(TARGET "${target}" APPEND_STRING PROPERTY LINK_FLAGS " -static")

        # Or (haven't tested this), if CMake 3.13+ is used:
        #target_link_options("${target}" PRIVATE -static)
    endif()
endfunction()

function(_cc_static_runtime target)
    if(is_msvc)
        _cc_static_runtime_msvc("${target}")
    elseif(is_gcc)
        _cc_static_runtime_gcc("${target}")
    endif()
endfunction()

# Symbol stripping routines:

function(_cc_strip_symbols_gcc target)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        set(release_build $<OR:$<CONFIG:Release>,$<CONFIG:MinSizeRel>>)
        if(release_build)
            # This causes issues with mixing keyword- and plain- versions of
            # target_link_libraries:
            #target_link_libraries("${target}" PRIVATE -s)

            set_property(TARGET "${target}" APPEND_STRING PROPERTY LINK_FLAGS " -s")
        endif()
    endif()
endfunction()

function(_cc_strip_symbols target)
    if(is_gcc)
        _cc_strip_symbols_gcc("${target}")
    endif()
endfunction()

# Main macros:

function(_cc_apply_settings target)
    if(TARGET "${target}")
        get_target_property(target_imported "${target}" IMPORTED)
        if(NOT target_imported)
            if(CC_BEST_PRACTICES)
                _cc_best_practices("${target}")
            endif()
            if(CC_WINDOWS_DEF)
                _cc_common_windows_definitions("${target}")
            endif()
            if(CC_STRIP_SYMBOLS)
                _cc_strip_symbols("${target}")
            endif()
            if(CC_STATIC_RUNTIME)
                _cc_static_runtime("${target}")
            endif()
        endif()
    endif()
endfunction()

if(NOT parent_dir)
    macro(add_executable target)
        _add_executable(${ARGV})
        _cc_apply_settings("${target}")
    endmacro()

    macro(add_library target)
        _add_library(${ARGV})
        _cc_apply_settings("${target}")
    endmacro()
endif()
