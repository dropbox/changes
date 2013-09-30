#!/usr/bin/env python

import itertools
import os
import random
import sys
import uuid

from changes.config import db, create_app
from changes.constants import Status, Result
from changes.models import (
    Project, Repository, Author, Revision, Build, Phase, Step, Test, Change
)


app = create_app()
app_context = app.app_context()
app_context.push()


answer = raw_input('This will wipe all data in the `changes` database!\nDo you wish to continue? [yN] ').lower()
if answer != 'y':
    sys.exit(1)

assert not os.system('dropdb --if-exists changes')
assert not os.system('createdb -E utf-8 changes')
assert not os.system('alembic upgrade head')

TEST_LABELS = itertools.cycle([
    'tests/changes/handlers/test_xunit.py:test_result_generation',
    'tests/changes/handlers/test_coverage.py:test_result_generation',
    'tests/changes/backends/koality/test_backend.py:ListBuildsTest.test_simple',
    'tests/changes/backends/koality/test_backend.py:SyncBuildDetailsTest.test_simple',
])

TEST_STEP_LABELS = itertools.cycle([
    'tests/changes/web/frontend/test_build_list.py',
    'tests/changes/web/frontend/test_build_details.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/handlers/test_xunit.py',
])


def generate_build(revision, status=Status.finished, result=Result.passed):
    label = 'D%s: %s' % (random.randint(1000, 100000), revision.message.splitlines()[0])[:128]

    change = Change(
        hash=uuid.uuid4().hex,
        label=label,
        project=project,
        repository=repository,
        author=revision.author,
    )

    build = Build(
        change=change,
        repository=revision.repository,
        project=project,
        parent_revision_sha=revision.sha,
        author=revision.author,
        status=status,
        result=result,
        label=label,
    )
    db.session.add(build)

    phase1_setup = Phase(
        repository=build.repository, project=build.project, build=build,
        status=status, result=result, label='Setup',
    )
    db.session.add(phase1_setup)

    phase1_compile = Phase(
        repository=build.repository, project=build.project, build=build,
        status=status, result=result, label='Compile',
    )
    db.session.add(phase1_compile)

    phase1_test = Phase(
        repository=build.repository, project=build.project, build=build,
        status=status, result=result, label='Test',
    )
    db.session.add(phase1_test)

    step = Step(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=status, result=result,
        label=TEST_STEP_LABELS.next(),
    )
    db.session.add(step)
    step = Step(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=status, result=result,
        label=TEST_STEP_LABELS.next(),
    )
    db.session.add(step)

    return build


def generate_revision(repository, author):
    revision = Revision(
        repository=repository, sha=uuid.uuid4().hex, author=author,
        message='Correct some initial schemas and first draft at some mock datageneration\n\n'
                'https://github.com/dcramer/changes/commit/68d1c899e3c821c920ea3baf244943b10ed273b5'
    )
    db.session.add(revision)

    return revision


def generate_test_results(build, result=Result.passed):
    test = Test(
        build=build, project=build.project,
        result=result, label=TEST_LABELS.next(),
        duration=random.randint(0, 3000),
    )
    db.session.add(test)

    return test


repository = Repository(
    url='https://github.com/example/example.git')
db.session.add(repository)

project = Project(
    slug='example', name='example', repository=repository)
db.session.add(project)

author = Author(name='David Cramer', email='dcramer@gmail.com')
db.session.add(author)

# generate a bunch of builds
for _ in xrange(50):
    result = Result.failed if random.randint(0, 10) > 7 else Result.passed

    revision = generate_revision(repository, author)
    db.session.add(revision)

    build = generate_build(
        revision=revision,
        result=result,
    )
    for _ in xrange(50):
        generate_test_results(build, result)

db.session.commit()
