# oldstable as of May '26.
cmake_minimum_required(VERSION 3.25)

project(example_boost)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Boost CONFIG REQUIRED COMPONENTS filesystem)
add_executable(foo foo.cpp)
target_link_libraries(foo PRIVATE Boost::disable_autolinking Boost::filesystem)

install(TARGETS foo RUNTIME DESTINATION bin)
