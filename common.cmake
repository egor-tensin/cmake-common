# Copyright (c) 2017 Egor Tensin <Egor.Tensin@gmail.com>
# Distributed under the MIT License.

# It's a CMake code snippet I use in all of my CMake projects.
# It makes targets link the runtime statically by default, strips debug symbols
# in release builds and sets a couple of useful compilation options.

# Add this to the top-level CMakeLists.txt (unless a higher version has already
# been specified):
#
#     cmake_minimum_required(VERSION 3.1)

# Otherwise this line:
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

if(CMAKE_C_COMPILER)
    set(toolset "${CMAKE_C_COMPILER_ID}")
elseif(CMAKE_CXX_COMPILER)
    set(toolset "${CMAKE_CXX_COMPILER_ID}")
else()
    set(toolset "unknown")
endif()
message(STATUS "Toolset: ${toolset}")

if(toolset STREQUAL "GNU")
    set(is_gcc ON)
elseif(toolset STREQUAL "MSVC")
    set(is_msvc ON)
else()
    message(WARNING "Unrecognized toolset: ${toolset}")
endif()

# Compilation options almost always useful:

function(best_practices_msvc target)
    set(compile_options /MP /W4)
    set(compile_definitions WIN32_LEAN_AND_MEAN NOMINMAX)
    get_target_property(target_type "${target}" TYPE)
    if(target_type STREQUAL "INTERFACE_LIBRARY")
        target_compile_definitions("${target}" INTERFACE ${compile_definitions})
    else()
        target_compile_options("${target}" PRIVATE ${compile_options})
        target_compile_definitions("${target}" PRIVATE ${compile_definitions})
    endif()
endfunction()

function(best_practices_gcc target)
    set(compile_options -Wall -Wextra)
    get_target_property(target_type "${target}" TYPE)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY")
        target_compile_options("${target}" PRIVATE ${compile_options})
    endif()
endfunction()

function(best_practices target)
    if(is_msvc)
        best_practices_msvc("${target}")
    elseif(is_gcc)
        best_practices_gcc("${target}")
    endif()
endfunction()

# User-defined switches:

set(default_value ON)
get_directory_property(parent_directory PARENT_DIRECTORY)
if(parent_directory)
    set(default_value OFF)
endif()

option(CC_BEST_PRACTICES "Apply generally useful compilation options" "${default_value}")
option(CC_STATIC_RUNTIME "Link the runtime statically"    "${default_value}")
#option(CC_STATIC_BOOST   "Use the static Boost libraries" "${default_value}")
option(CC_STRIP_SYMBOLS  "Strip debug symbols"            "${default_value}")
set(CC_CXX_STANDARD "14" CACHE STRING "C++ standard version")

option(Boost_USE_STATIC_LIBS "Use the static Boost libraries" "${default_value}")
option(Boost_USE_STATIC_RUNTIME "Use Boost libraries linked to the runtime statically" "${CC_STATIC_RUNTIME}")

message(STATUS "C++ standard:                   ${CC_CXX_STANDARD}")
message(STATUS "Best practices:                 ${CC_BEST_PRACTICES}")
message(STATUS "Use the static Boost libraries: ${Boost_USE_STATIC_LIBS}")
message(STATUS "Link the runtime statically:    ${CC_STATIC_RUNTIME}")
message(STATUS "Strip symbols:                  ${CC_STRIP_SYMBOLS}")

# C++ standard version:

set(CMAKE_CXX_STANDARD "${CC_CXX_STANDARD}")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Static runtime routines:

function(static_runtime_msvc target)
    get_target_property(target_type "${target}" TYPE)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY")
        target_compile_options("${target}" PRIVATE
            $<$<CONFIG:Debug>:/MTd>
            $<$<NOT:$<CONFIG:Debug>>:/MT>)
    endif()
endfunction()

function(static_runtime_gcc target)
    get_target_property(target_type "${target}" TYPE)
    if(target_type STREQUAL "EXECUTABLE")
        target_link_libraries("${target}" PRIVATE -static)
    endif()
endfunction()

function(static_runtime target)
    if(is_msvc)
        static_runtime_msvc("${target}")
    elseif(is_gcc)
        static_runtime_gcc("${target}")
    endif()
endfunction()

# Symbol stripping routines:

function(strip_symbols_gcc target)
    get_target_property(target_type "${target}" TYPE)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY")
        set(release_build $<OR:$<CONFIG:Release>,$<CONFIG:MinSizeRel>>)
        target_link_libraries("${target}" PRIVATE $<${release_build}:-s>)
    endif()
endfunction()

function(strip_symbols target)
    if(is_gcc)
        strip_symbols_gcc("${target}")
    endif()
endfunction()

# Main macros:

function(apply_common_settings target)
    if(TARGET "${target}")
        get_target_property(target_imported "${target}" IMPORTED)
        if(NOT target_imported)
            if(CC_BEST_PRACTICES)
                best_practices("${target}")
            endif()
            if(CC_STRIP_SYMBOLS)
                strip_symbols("${target}")
            endif()
            if(CC_STATIC_RUNTIME)
                static_runtime("${target}")
            endif()
        endif()
    endif()
endfunction()

macro(add_executable target)
    _add_executable(${ARGV})
    apply_common_settings("${target}")
endmacro()

macro(add_library target)
    _add_library(${ARGV})
    apply_common_settings("${target}")
endmacro()
