cmake_minimum_required(VERSION 3.1)

project(example_static)

include(../../common.cmake)

add_library(bar bar.cpp)
target_include_directories(bar PUBLIC .)

add_executable(foo foo.cpp)
target_link_libraries(foo PRIVATE bar)

install(TARGETS foo bar RUNTIME DESTINATION bin ARCHIVE DESTINATION lib)
install_pdbs(TARGETS foo DESTINATION bin)
