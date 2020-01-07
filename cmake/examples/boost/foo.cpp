#include <boost/filesystem.hpp>

#include <iostream>

int main(int argc, char* argv[]) {
    std::cout << boost::filesystem::absolute(boost::filesystem::path{argv[0]}).string() << "\n";
    return 0;
}
