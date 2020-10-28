cmake_minimum_required(VERSION 3.1)

project(example_dynamic)

include(../../common.cmake)

add_library(baz SHARED baz.cpp)
target_include_directories(baz PUBLIC .)

add_executable(foo foo.cpp)
target_link_libraries(foo PRIVATE baz)

install(TARGETS foo baz RUNTIME DESTINATION bin LIBRARY DESTINATION lib)
install_pdbs(TARGETS foo baz DESTINATION bin)
