cmake_minimum_required(VERSION 3.5) # for Boost::* imported targets

project(example_boost)

include(../../common.cmake)

find_package(Boost REQUIRED COMPONENTS filesystem)
add_executable(foo foo.cpp)
target_link_libraries(foo PRIVATE Boost::disable_autolinking Boost::filesystem)

install(TARGETS foo RUNTIME DESTINATION bin)
install_pdbs(TARGETS foo DESTINATION bin)
