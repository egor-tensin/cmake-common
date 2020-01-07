cmake_minimum_required(VERSION 3.1)

project(example_dynamic)

include(../../common.cmake)

add_library(bar SHARED bar.cpp)
target_include_directories(bar PUBLIC .)

add_executable(foo foo.cpp)
target_link_libraries(foo PRIVATE bar)

install(TARGETS foo bar RUNTIME DESTINATION bin LIBRARY DESTINATION lib)
