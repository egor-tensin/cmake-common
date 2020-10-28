cmake_minimum_required(VERSION 3.1)

project(example_simple)

include(../../common.cmake)

add_executable(foo foo.cpp)

install(TARGETS foo RUNTIME DESTINATION bin)
install_pdbs(TARGETS foo DESTINATION bin)
