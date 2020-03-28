Boost
=====

Download & build the Boost libraries in a cross-platform way.
Consult the output of `build.py --help` for details.

A simple usage example to download and build Boost 1.71.0:

    $ python3 build.py download 1.71.0
    ...

    $ python3 build.py build -- boost_1_71_0/ --with-filesystem --with-program_options
    ...
