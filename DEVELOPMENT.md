Development
-----------

Make a git tag:

    git tag "v$( python -m setuptools_scm --strip-dev )"

You can then review that the tag is fine and push w/ `git push --tags`.
