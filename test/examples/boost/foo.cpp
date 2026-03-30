#include <boost/filesystem.hpp>

#include <iostream>

int main(int argc, char* argv[]) {
    namespace fs = boost::filesystem;
    std::cout << argv[0] << '\n';
    for (int i = 1; i < argc; ++i) {
        std::cout << fs::absolute(boost::filesystem::path{argv[i]}).string()
                  << '\n';
    }
    return 0;
}
