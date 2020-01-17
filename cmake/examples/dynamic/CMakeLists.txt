cmake_minimum_required(VERSION 3.1)

project(example_dynamic)

include(../../common.cmake)

add_library(baz SHARED baz.cpp)
target_include_directories(baz PUBLIC .)

add_executable(foo foo.cpp)
target_link_libraries(foo PRIVATE baz)

install(TARGETS foo baz RUNTIME DESTINATION bin LIBRARY DESTINATION lib)
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    install(FILES "$<TARGET_PDB_FILE:foo>" "$<TARGET_PDB_FILE:baz>" DESTINATION bin OPTIONAL)
endif()
