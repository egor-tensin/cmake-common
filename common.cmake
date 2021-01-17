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

# Toolset identification
# ----------------------

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
elseif(toolset STREQUAL "Clang")
    set(is_clang ON)
else()
    message(WARNING "common.cmake: Unrecognized toolset: ${toolset}")
endif()

# User-defined switches
# ---------------------

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
    endif()
    option(CC_STATIC_RUNTIME "Link the runtime statically" "${static_runtime_default_value}")
endif()
if(NOT DEFINED CC_STRIP_SYMBOLS)
    option(CC_STRIP_SYMBOLS  "Strip debug symbols" "${default_value}")
endif()

option(Boost_USE_STATIC_LIBS "Use the static Boost libraries" "${default_value}")
option(Boost_USE_STATIC_RUNTIME "Use Boost libraries linked to the runtime statically" "${CC_STATIC_RUNTIME}")

if(NOT parent_dir)
    message(STATUS "common.cmake: Toolset:                 ${toolset}")
    message(STATUS "common.cmake: C++ standard:            ${CC_CXX_STANDARD}")
    message(STATUS "common.cmake: Common compiler options: ${CC_BEST_PRACTICES}")
    message(STATUS "common.cmake: Useful Windows macros:   ${CC_WINDOWS_DEF}")
    message(STATUS "common.cmake: Static Boost libraries:  ${Boost_USE_STATIC_LIBS}")
    message(STATUS "common.cmake: Static runtime:          ${CC_STATIC_RUNTIME}")
    message(STATUS "common.cmake: Strip symbols:           ${CC_STRIP_SYMBOLS}")
endif()

# C++ standard
# ------------

set(CMAKE_CXX_STANDARD "${CC_CXX_STANDARD}")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Common compiler options
# -----------------------

function(_cc_best_practices_msvc target)
    set(compile_options /MP /W4)
    target_compile_options("${target}" PRIVATE ${compile_options})
endfunction()

function(_cc_best_practices_gcc target)
    set(compile_options -Wall -Wextra)
    target_compile_options("${target}" PRIVATE ${compile_options})
endfunction()

function(_cc_best_practices target)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        message(STATUS "common.cmake: ${target}: Settings common compiler options")
        if(is_msvc)
            _cc_best_practices_msvc("${target}")
        elseif(is_gcc)
            _cc_best_practices_gcc("${target}")
        endif()
    endif()
endfunction()

# Useful Windows macros
# ---------------------

function(_cc_common_windows_definitions target)
    set(compile_definitions WIN32_LEAN_AND_MEAN NOMINMAX)
    get_target_property(target_type "${target}" TYPE)
    if(target_type STREQUAL "INTERFACE_LIBRARY")
        message(STATUS "common.cmake: ${target}: Defining useful Windows macros")
        target_compile_definitions("${target}" INTERFACE ${compile_definitions})
    else()
        get_target_property(aliased "${target}" ALIASED_TARGET)
        if(NOT aliased)
            message(STATUS "common.cmake: ${target}: Defining useful Windows macros")
            target_compile_definitions("${target}" PRIVATE ${compile_definitions})
        endif()
    endif()
endfunction()

# Static runtime
# --------------

function(_cc_join output glue)
    set(tmp "")
    set(this_glue "")
    foreach(arg ${ARGN})
        set(tmp "${tmp}${this_glue}${arg}")
        set(this_glue "${glue}")
    endforeach()
    set("${output}" "${tmp}" PARENT_SCOPE)
endfunction()

function(_cc_replace_flags str sub)
    # Whenever this is used, it fucking sucks, but was tested on at least some
    # CMake version.
    set(flags_list
        CMAKE_CXX_FLAGS
        CMAKE_CXX_FLAGS_DEBUG
        CMAKE_CXX_FLAGS_RELWITHDEBINFO
        CMAKE_CXX_FLAGS_RELEASE
        CMAKE_CXX_FLAGS_MINSIZEREL
        CMAKE_C_FLAGS
        CMAKE_C_FLAGS_DEBUG
        CMAKE_C_FLAGS_RELWITHDEBINFO
        CMAKE_C_FLAGS_RELEASE
        CMAKE_C_FLAGS_MINSIZEREL)
    foreach(flags ${flags_list})
        if(NOT ${flags})
            continue()
        endif()
        set(value "${${flags}}")
        string(REPLACE "${str}" "${sub}" value "${value}")
        get_property(original_docstring CACHE ${flags} PROPERTY HELPSTRING)
        set(${flags} "${value}" CACHE STRING "${original_docstring}" FORCE)
    endforeach()
endfunction()

# MSVC_RUNTIME_LIBRARY is a convenient way to select the runtime library, but
# it's only available starting from 3.15.
# Additionally, it has to be enabled outside of this file (either via
# cmake_policy or setting the cmake_minimum_required to the appropriate value).

if(POLICY CMP0091)
    cmake_policy(GET CMP0091 msvc_runtime_policy)
    # Use a variable as an indicator that the policy is in effect.
    if(msvc_runtime_policy STREQUAL "NEW")
        set(msvc_runtime_policy ON)
    else()
        unset(msvc_runtime_policy)
    endif()
endif()

function(_cc_static_runtime_via_policy target)
    set_property(TARGET "${target}" PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endfunction()

function(_cc_static_runtime_msvc target)
    if(msvc_runtime_policy)
        _cc_static_runtime_via_policy("${target}")
    else()
        _cc_replace_flags("/MDd" "/MTd")
        _cc_replace_flags("/MD" "/MT")
    endif()
endfunction()

function(_cc_static_runtime_gcc target)
    # This causes issues with mixing keyword- and plain- versions of
    # target_link_libraries:
    #target_link_libraries("${target}" PRIVATE -static)

    set(flags -static-libstdc++ -static-libgcc)
    if(CYGWIN)
        set(flags -static-libgcc)
    endif()

    if(CMAKE_VERSION VERSION_LESS "3.13")
        _cc_join(flags_str " " ${flags})
        set_property(TARGET "${target}" APPEND_STRING PROPERTY LINK_FLAGS " ${flags_str}")
    else()
        target_link_options("${target}" PRIVATE ${flags})
    endif()
endfunction()

function(_cc_static_runtime_clang target)
    if(NOT WIN32)
        # On Linux, clang/clang++ is used, which is treated as GCC.
        # This is consistent with CMake (see Modules/Platform/Linux-Clang-CXX.cmake).
        _cc_static_runtime_gcc("${target}")
        return()
    endif()

    # On Windows, clang/clang++ can be used since 3.15; otherwise, clang-cl is
    # is used, which is treated as MSVC.
    # This is consistent with CMake (see Modules/Platform/Windows-Clang.cmake).
    if(CMAKE_VERSION VERSION_LESS "3.15")
        _cc_static_runtime_msvc("${target}")
        return()
    endif()

    # If the policy is enabled, we don't need to patch the flags manually.
    if(msvc_runtime_policy)
        _cc_static_runtime_via_policy("${target}")
        return()
    endif()

    if("${CMAKE_CXX_COMPILER_FRONTEND_VARIANT}" STREQUAL "MSVC" OR "${CMAKE_C_COMPILER_FRONTEND_VARIANT}" STREQUAL "MSVC")
        # It's 3.15 or higher, but we're in luck: clang-cl is used, which can
        # be treated as MSVC.
        _cc_static_runtime_msvc("${target}")
        return()
    endif()

    # Well, that sucks, but works for versions 3.15--3.18 at least.
    _cc_replace_flags("-D_DLL" "")
    _cc_replace_flags("--dependent-lib=msvcrt" "--dependent-lib=libcmt")
endfunction()

function(_cc_static_runtime target)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        message(STATUS "common.cmake: ${target}: Linking the runtime statically")
        if(is_msvc)
            _cc_static_runtime_msvc("${target}")
        elseif(is_gcc)
            _cc_static_runtime_gcc("${target}")
        elseif(is_clang)
            _cc_static_runtime_clang("${target}")
        endif()
    endif()
endfunction()

# Symbol stripping
# ----------------

function(_cc_strip_symbols_gcc target)
    # This causes issues with mixing keyword- and plain- versions of
    # target_link_libraries:
    #target_link_libraries("${target}" PRIVATE -s)

    set_property(TARGET "${target}" APPEND_STRING PROPERTY LINK_FLAGS_RELEASE " -s")
    set_property(TARGET "${target}" APPEND_STRING PROPERTY LINK_FLAGS_MINSIZEREL " -s")
endfunction()

function(_cc_strip_symbols target)
    get_target_property(target_type "${target}" TYPE)
    get_target_property(aliased "${target}" ALIASED_TARGET)
    if(NOT target_type STREQUAL "INTERFACE_LIBRARY" AND NOT aliased)
        message(STATUS "common.cmake: ${target}: Stripping symbols for release configurations")
        if(is_gcc OR is_clang)
            _cc_strip_symbols_gcc("${target}")
        endif()
    endif()
endfunction()

# Main macros
# -----------

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

function(install_pdbs)
    if(NOT is_msvc)
        return()
    endif()
    cmake_parse_arguments(INSTALL_PDBS "" "DESTINATION" "TARGETS" ${ARGN})
    if(NOT INSTALL_PDBS_DESTINATION)
        message(FATAL_ERROR "common.cmake: install_pdbs: please specify DESTINATION")
    endif()
    if(NOT INSTALL_PDBS_TARGETS)
        message(FATAL_ERROR "common.cmake: install_pdbs: please specify TARGETS")
    endif()
    if(INSTALL_PDBS_UNPARSED_ARGUMENTS)
        message(FATAL_ERROR "common.cmake: install_pdbs: unrecognized arguments: ${INSTALL_PDBS_UNPARSED_ARGUMENTS}")
    endif()
    foreach(target ${INSTALL_PDBS_TARGETS})
        list(APPEND pdbs "$<TARGET_PDB_FILE:${target}>")
    endforeach()
    install(FILES ${pdbs} DESTINATION ${INSTALL_PDBS_DESTINATION} OPTIONAL)
endfunction()
