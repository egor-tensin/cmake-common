cmake_minimum_required(VERSION 3.1)

project(example_simple)

include(../../common.cmake)

add_executable(foo foo.cpp)

install(TARGETS foo RUNTIME DESTINATION bin)
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    install(FILES "$<TARGET_PDB_FILE:foo>" DESTINATION bin OPTIONAL)
endif()
