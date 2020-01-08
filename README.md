cmake-common
============

Various utility files to build my CMake projects, as those seem to overlap
between different projects quite a bit.

This repository is intended to be included as a submodule.
Git submodules are relatively hard to use though, but there's [an excellent
guide] to help you through.

[an excellent guide]: https://medium.com/@porteneuve/mastering-git-submodules-34c65e940407

Usage
-----

Using the scripts in this project, you can build

* [Boost],
* a [CMake project].

All in a relatively cross-platform way.

It's used in a bunch of projects of mine, namely in

* [aes-tools],
* [math-server]

and a few others.

[Boost]: boost/build/README.md
[CMake project]: cmake/build/README.md

[aes-tools]: https://github.com/egor-tensin/aes-tools
[math-server]: https://github.com/egor-tensin/math-server

License
-------

Distributed under the MIT License.
See [LICENSE.txt] for details.

[LICENSE.txt]: LICENSE.txt
