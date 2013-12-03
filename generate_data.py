#!/usr/bin/env python

import os
import random
import sys

from changes import mock
from changes.config import db, create_app
from changes.constants import Result


app = create_app()
app_context = app.app_context()
app_context.push()


answer = raw_input('This will wipe all data in the `changes` database!\nDo you wish to continue? [yN] ').lower()
if answer != 'y':
    sys.exit(1)

assert not os.system('dropdb --if-exists changes')
assert not os.system('createdb -E utf-8 changes')
assert not os.system('alembic upgrade head')


repository = mock.repository()
project = mock.project(repository)

# generate a bunch of builds
for _ in xrange(50):
    result = Result.failed if random.randint(0, 10) > 7 else Result.passed

    author = mock.author()
    revision = mock.revision(repository, author)
    build = mock.build(
        revision=revision,
        result=result,
    )
    for _ in xrange(50):
        mock.test_result(build, result)
