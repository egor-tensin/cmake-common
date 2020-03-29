Boost
=====

Download & build the Boost libraries in a cross-platform way.

A simple usage example to download and build Boost 1.72.0:

    $ python3 -m project.boost.download 1.72.0
    ...

    $ python3 -m project.boost.build -- boost_1_72_0/ --with-filesystem --with-program_options
    ...
