#!/bin/bash -eux

# Allow the path to mypy to be specified in the MYPY environment variable, but default to "mypy".
: ${MYPY=mypy}

# Any paths we need to include in typechecking that are not automatically found (that is, that
# have no '# type:' annotation)
EXTRA_FILES=""

# Any files with type annotations that should be excluded from typechecking. This is a regular
# expression matched against the filenames.
EXCLUDE=""

# Find all Python files that are not in the exclude list and which have a '# type:' annotation.
FILES=`find . -type f -name \*.py -print0  \
       | xargs -0 grep -ls '# type:'`

if [ -n "$EXCLUDE" ]; then
    FILES=`echo "$FILES" | egrep -v "$EXCLUDE"`
fi

ci/run_mypy.py $MYPY --silent-imports --py2 $FILES $EXTRA_FILES
