CTest suffers from at least two issues, in particular with regard to its
PASS_REGULAR_EXPRESSION feature:

1. The regular expression syntax used by CMake is deficient.
2. The exit code of a test is ignored if one of the regexes matches.

`project-ctest-driver` (alternatively, `python -m project.ctest_driver`) tries
to fix them.

    $ project-ctest-driver run --pass-regex OK --fail-regex Fail -- path/to/executable arg1 arg2

In addition, it's a cross-platform `grep`:

    $ project-ctest-driver grep --pass-regex OK --fail-regex Fail -- path/to/logfile.log
