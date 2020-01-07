#include <boost/filesystem.hpp>

#include <iostream>

int main() {
    std::cout << boost::filesystem::path{argv0}.absolute().string(); << "\n";
    return 0;
}
