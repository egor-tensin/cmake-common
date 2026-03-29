cmake_minimum_required(VERSION 3.15)

project(example_simple)

add_executable(foo foo.cpp)

install(TARGETS foo RUNTIME DESTINATION bin)
