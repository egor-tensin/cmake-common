# Copyright (c) 2017 Egor Tensin <Egor.Tensin@gmail.com>
# It's a CMake code snippet I use in all of my CMake projects.
# It makes targets link the runtime statically by default + strips debug
# symbols in release builds.
# The latest version can be found at
# https://github.com/egor-tensin/cmake-common.
# Distributed under the MIT License.

# Version: 2019-11-29T22:30:28Z

get_directory_property(parent_directory PARENT_DIRECTORY)
set(is_root_project $<NOT:parent_directory>)

if(CMAKE_C_COMPILER)
    set(toolset "${CMAKE_C_COMPILER_ID}")
elseif(CMAKE_CXX_COMPILER)
    set(toolset "${CMAKE_CXX_COMPILER_ID}")
else()
    set(toolset "unknown")
endif()

set(USE_STATIC_RUNTIME "${is_root_project}" CACHE BOOL "Link the runtime statically")
set(STRIP_SYMBOL_TABLE "${is_root_project}" CACHE BOOL "Strip symbol tables")
set(CXX_STANDARD "17" CACHE BOOL "Set C++ standard version")

if(is_root_project)
    if(MSVC)
        add_compile_options(/MP /W4)
    elseif(CMAKE_COMPILER_IS_GNUCC OR CMAKE_COMPILER_IS_GNUCXX)
        add_compile_options(-Wall -Wextra)
    else()
        message(WARNING "Unrecognized toolset: ${toolset}")
    endif()
endif()

set(CMAKE_CXX_STANDARD "${CXX_STANDARD}")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(use_static_runtime_msvc target)
    get_target_property(target_type "${target}" TYPE)
    if(target_type STREQUAL INTERFACE_LIBRARY)
    else()
        target_compile_options("${target}" PRIVATE
            $<$<CONFIG:Debug>:/MTd>
            $<$<NOT:$<CONFIG:Debug>>:/MT>)
    endif()
endfunction()

function(use_static_runtime_gcc target)
    get_target_property(target_type "${target}" TYPE)
    if(target_type STREQUAL EXECUTABLE)
        target_link_libraries("${target}" PRIVATE -static)
    endif()
endfunction()

function(use_static_runtime target)
    if(MSVC)
        use_static_runtime_msvc("${target}")
    elseif(CMAKE_COMPILER_IS_GNUCC OR CMAKE_COMPILER_IS_GNUCXX)
        use_static_runtime_gcc("${target}")
    else()
        message(WARNING "Unrecognized toolset: ${toolset}")
    endif()
endfunction()

function(strip_symbol_table_gcc target)
    get_target_property(target_type "${target}" TYPE)
    set(release_build $<OR:$<CONFIG:Release>,$<CONFIG:MinSizeRel>>)
    if(target_type STREQUAL INTERFACE_LIBRARY)
    else()
        target_link_libraries("${target}" PRIVATE $<${release_build}:-s>)
    endif()
endfunction()

function(strip_symbol_table target)
    if(MSVC)
    elseif(CMAKE_COMPILER_IS_GNUCC OR CMAKE_COMPILER_IS_GNUCXX)
        strip_symbol_table_gcc("${target}")
    else()
        message(WARNING "Unrecognized toolset: ${toolset}")
    endif()
endfunction()

function(apply_common_settings target)
    if(TARGET "${target}")
        get_target_property(target_imported "${target}" IMPORTED)
        if(target_imported STREQUAL NOTFOUND OR NOT target_imported)
            if(STRIP_SYMBOL_TABLE)
                strip_symbol_table("${target}")
            endif()
            if(USE_STATIC_RUNTIME)
                use_static_runtime("${target}")
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
