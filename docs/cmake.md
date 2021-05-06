Default generator
-----------------

As of CMake 3.18, the default generator (unless set explicitly) is:

  * the newest Visual Studio or "NMake Makefiles" on Windows,
  * "Unix Makefiles" otherwise.

This is regardless of whether any executables like gcc, cl or make are
available ([1][1]).

Makefile generators
-------------------

CMake has a number of "... Makefiles" generators.  "Unix Makefiles" uses
gmake/make/smake, whichever is found first, and cc/c++ for compiler detection
([2][2]).  "MinGW Makefiles" looks for mingw32-make.exe in a number of
well-known locations, uses gcc/g++ directly, and is aware of windres ([3][3]).
In addition, "Unix Makefiles" uses /bin/sh as the SHELL value in the Makefile,
while the MinGW version uses cmd.exe.  I don't think it matters on Windows
though, since the non-existent /bin/sh is ignored anyway ([4][4]).  "NMake
Makefiles" is similar, except it defaults to using cl ([5][5]).

It's important to _not_ use the -A parameter with any of the Makefile
generators - it's an error.  This goes for "NMake Makefiles" also.  "NMake
Makefiles" doesn't attempt to search for installed Visual Studio compilers, you
need to use it from one of the Visual Studio-provided shells.

Visual Studio generators
------------------------

These are special.  They ignore the CMAKE_\<LANG\>_COMPILER parameters and use
cl by default ([9][9]).  They support specifying the toolset to use via the -T
parameter (the "Platform Toolset" value in the project's properties) since 3.18
([10][10]).  The toolset list varies between Visual Studio versions, and I'm
too lazy to learn exactly which version supports which toolsets.

`cmake --build` uses msbuild with Visual Studio generators.  You can pass the
path to a different cl.exe by doing something like

    msbuild ... /p:CLToolExe=another-cl.exe /p:CLToolPath=C:\parent\dir

It's important that the generators for Visual Studio 2017 or older use Win32 as
the default platform ([12][12]).  Because of that, we need to pass the -A
parameter.

mingw32-make vs make
--------------------

No idea what the actual differences are.  The explanation in the FAQ ([6][6])
about how GNU make "is lacking in some functionality and has modified
functionality due to the lack of POSIX on Win32" isn't terribly helpful.

It's important that you can install either on Windows (`choco install make` for
GNU make and `choco install mingw` to install a MinGW-w64 distribution with
mingw32-make.exe included).  Personally, I don't see any difference between
using either make.exe or mingw32-make.exe w/ CMake on Windows.  But, since
MinGW-w64 distributions do include mingw32-make.exe and not make.exe, we'll try
to detect that.

Cross-compilation
-----------------

If you want to e.g. build x86 binaries on x64 and vice versa, the easiest way
seems to be to make a CMake "toolset file", which initializes the proper
compiler flags (like -m64/-m32, etc.).  Such file could look like this:

    set(CMAKE_C_COMPILER   gcc)
    set(CMAKE_C_FLAGS      -m32)
    set(CMAKE_CXX_COMPILER g++)
    set(CMAKE_CXX_FLAGS    -m32)

You can then pass the path to it using the CMAKE_TOOLCHAIN_FILE parameter.

If you use the Visual Studio generators, just use the -A parameter: `-A Win32`.

As a side note, if you want to cross-compile between x86 and x64 using GCC on
Ubuntu, you need to install the gcc-multilib package.

Windows & Clang
---------------

Using Clang on Windows is no easy task, of course.  Prior to 3.15, there was no
support for building things using the clang++.exe executable, only clang-cl.exe
was supported ([7][7]).  If you specified `-DCMAKE_CXX_COMPILER=clang++`, CMake
would stil pass MSVC-style command line options to the compiler (like `/MD`,
`/nologo`, etc.), which clang++ doesn't like ([8][8]).

So, in summary, you can only use clang++ since 3.15.  clang-cl doesn't work
with Visual Studio generators unless you specify the proper toolset using the
-T parameter.  You can set the ClToolExe property using msbuild, but while that
might work in practice, clang-cl.exe needs to map some unsupported options for
everything to work properly.  For an example of how this is done, see the
LLVM.Cpp.Common.* files at ([11][11]).

I recommend using Clang (either clang-cl or clang++ since 3.15) using the
"NMake Makefiles" generator.

[1]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmake.cxx#L1697
[2]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmGlobalUnixMakefileGenerator3.cxx
[3]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmGlobalMinGWMakefileGenerator.cxx
[4]: https://www.gnu.org/software/make/manual/html_node/Choosing-the-Shell.html
[5]: https://github.com/Kitware/CMake/blob/v3.18.4/Source/cmGlobalNMakeMakefileGenerator.cxx
[6]: http://mingw.org/wiki/FAQ
[7]: https://cmake.org/cmake/help/v3.15/release/3.15.html#compilers
[8]: https://github.com/Kitware/CMake/blob/v3.14.7/Modules/Platform/Windows-Clang.cmake
[9]: https://gitlab.kitware.com/cmake/cmake/-/issues/19174
[10]: https://cmake.org/cmake/help/v3.8/release/3.8.html
[11]: https://github.com/llvm/llvm-project/tree/e408935bb5339e20035d84307c666fbdd15e99e0/llvm/tools/msbuild
[12]: https://cmake.org/cmake/help/v3.18/generator/Visual%20Studio%2015%202017.html
