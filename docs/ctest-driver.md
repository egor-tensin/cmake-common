CTest suffers from at least two issues, in particular with regard to its
PASS_REGULAR_EXPRESSION feature:

1. The regular expression syntax used by CMake is deficient.
2. The exit code of a test is ignored if one of the regexes matches.

`ctest-driver.py` tries to fix them.

    $ python3 path/to/tools/ctest-driver.py run --pass-regex OK --fail-regex Fail -- path/to/executable arg1 arg2

In addition, it's a cross-platform `grep`:

    $ python3 path/to/tools/ctest-driver.py grep --pass-regex OK --fail-regex Fail -- path/to/logfile.log
