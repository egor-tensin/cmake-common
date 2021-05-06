Library naming
--------------

The way Boost names library files by default is insane.  It's absolutely not
compatible between OSs, compilers, Boost versions, etc.  On Linux, for example,
it would create stage/lib/libboost_filesystem.a, while on Windows it would
become something insane like stage\lib\libboost_filesystem-vc142-mt-s-x64-1_72.lib.
More than that, older Boost versions don't include architecture information
(the "x64" part) in the file name, so you cannot store libraries for both x86
and x64 in the same directory.  On Linux, on the other hand, you can't even
store debug/release binaries in the same directory.  What's worse is that older
CMake versions don't support the architecture suffix, choking on the Windows
example above.

With all of that in mind, I decided to bring some uniformity by sacrificing
some flexibility. b2 is called with `--layout=system`, and libraries are put to
stage/\<platform\>/\<configuration\>/lib, where \<platform\> is x86/x64 and
\<configuration\> is CMake's CMAKE_BUILD_TYPE.  That means that I can't have
libraries with different runtime-link values in the same directory, but I don't
really care.

Hate speech
-----------

Is there a person who doesn't hate Boost.Build?  I'm not sure, I'm definitely
_not_ one of these people.  Maybe it's the lack of adoption (meaning that
learning it is useless outside of Boost), maybe it's the incomprehensible
syntax.  Maybe it's the absolutely insane compiler-specific configuration files
(tools/build/src/tools/*.jam), which are impossible to figure out. Maybe it's
the fact that the implementation switched from C to C++ while some half-baked
Python implementation has been there since at least 2015 (see the marvelous
memo "Status: mostly ported." at the top of tools/build/src/build_system.py).

What I hate the most though is how its various subtle, implicit and invisible
decision-making heuristics changed thoughout the release history of Boost.  You
have a config and a compiler that will happily build version 1.65.0?  Great!
Want to use the same config and the same compiler to build version 1.72.0?
Well, too fucking bad, it doesn't work anymore.  This I really do hate the
most.

Three kinds of toolsets
-----------------------

b2 accepts the `toolset=` parameter.  What about building b2 itself though?
Well, this is what the bootstrap.{sh,bat} scripts do.  They also accept a
toolset argument, but it is _completely_ different to that of b2.  That's sort
of OK, since e.g. cross-compiling b2 is something we rarely want to do (and
hence there must typically be a native toolset available).

bootstrap.sh and bootstrap.bat are completely different (of course!), and
accept different arguments for their toolset parameters.

Config file insanity
--------------------

Say, we're building Boost on Windows using the GCC from a MinGW-w64
distribution.  We can pass `toolset=gcc` and all the required flags on the
command line no problem.  What if we want to make a user configuration file so
that 1) the command line is less polluted, and 2) it can possibly be shared?
Well, if we put

    using gcc : : : <name>value... ;

there, Boost 1.65.0 will happily build everything, while Boost 1.72.0 will
complain about "duplicate initialization of gcc".  This is because when we ran
`bootstrap.bat gcc` earlier, it wrote `using gcc ;` in project-config.jam.  And
while Boost 1.65.0 detects that `toolset=gcc` means we're going to use the
MinGW GCC, and magically turns `toolset=gcc` to `toolset=gcc-mingw`, Boost
1.72.0 does no such thing, and chokes on the "duplicate" GCC declaration.

We also cannot put

    using gcc : custom : : <options> ;

without the executable path, since Boost insists that `g++ -dumpversion` must
equal to "custom" (which makes total sense, lol).  So we have to force it, and
do provide the path.

Windows & Clang
---------------

Building Boost using Clang on Windows is a sad story.  As of 2020, there're
three main ways to install the native Clang toolset on Windows:

  * download the installer from llvm.org (`choco install llvm` does this)
    a.k.a. the upstream,
  * install it as part of a MSYS2 installation (`pacman -S mingw-w64-x86_64-clang`),
  * install as part of a Visual Studio installation.

Using the latter method, you can switch a project to use the LLVM toolset using
Visual Studio, but that's stupid.  The former two, on the other hand, give us
the the required clang/clang++/clang-cl executables, so everything seems to be
fine.

Except it's not fine.  Let's start with the fact that prior to 1.66.0,
`toolset=clang` is completely broken on Windows.  It's just an alias for
clang-linux, and it's hardcoded to require the ar & ranlib executables to
create static libraries.  Which is fine on Linux, since, and I'm quoting the
source, "ar is always available".  But it's not fine on Windows, since
ar/ranlib are not, in fact, available there by default.  Sure, you can install
some kind of MinGW toolset, and it might even work, but what the hell,
honestly?

Luckily, both the upstream distribution and the MSYS2 mingw-w64-x86_64-llvm
package come with the llvm-ar and llvm-ranlib utilities.  So we can put
something like this in the config:

    using clang : custom : clang++.exe : <archiver>llvm-ar <ranlib>llvm-ranlib.exe ;

and later call

    b2 toolset=clang-custom --user-config=path/to/config.jam ...

But, as I mentioned, prior to 1.66.0, `toolset=clang` is _hardcoded_ to use ar
& ranlib, these exact utility names.  So either get them as part of some MinGW
distribution or build Boost using another toolset.

Now, it's all fine, but building stuff on Windows adds another thing into the
equation: debug runtimes.  When you build Boost using MSVC, for example, it
picks one of the appropriate `/MT[d]` or `/MD[d]` flags to build the Boost
libraries with.  Emulating these flags with `toolset=clang` is complicated and
inconvenient.  Luckily, there's the clang-cl.exe executable, which aims to
provide command line interface compatible with that of cl.exe.

Boost.Build even supports `toolset=clang-win`, which should use clang-cl.exe.
But alas, it's completely broken prior to 1.69.0.  It just doesn't work at all.
So, if you want to build w/ clang-cl.exe, either use Boost 1.69.0 or later, or
build using another toolset.

Cygwin & Clang
--------------

Now, a few words about Clang on Cygwin.  When building 1.65.0, I encountered
the following error:

    /usr/include/w32api/synchapi.h:127:26: error: conflicting types for 'Sleep'
      WINBASEAPI VOID WINAPI Sleep (DWORD dwMilliseconds);
                             ^
    ./boost/smart_ptr/detail/yield_k.hpp:64:29: note: previous declaration is here
      extern "C" void __stdcall Sleep( unsigned long ms );
                                ^

GCC doesn't emit an error here because /usr/include is in a pre-configured
"system" include directories list, and the declaration there take precedence, I
guess?  The root of the problem BTW is that sizeof(unsigned long) is

  * 4 for MSVC and MinGW-born GCCs,
  * 8 for Clang (and, strangely, Cygwin GCC; why don't we get runtime
    errors?).

The fix is to add `define=BOOST_USE_WINDOWS_H`.  I don't even know what's the
point of not having it as a default.
