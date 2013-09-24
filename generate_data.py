#!/usr/bin/env python

import itertools
import os
import random
import sys
import uuid

from buildbox.db.backend import Backend
from buildbox.constants import Status, Result
from buildbox.models import (
    Project, Repository, Author, Revision, Build, Phase, Step, Test
)

answer = raw_input('This will wipe all data in the `buildbox` database!\nDo you wish to continue? [yN] ').lower()
if answer != 'y':
    sys.exit(1)

assert not os.system('dropdb --if-exists buildbox')
assert not os.system('createdb -E utf-8 buildbox')
assert not os.system('alembic upgrade head')

TEST_LABELS = itertools.cycle([
    'tests/buildbox/handlers/test_xunit.py:test_result_generation',
    'tests/buildbox/handlers/test_coverage.py:test_result_generation',
    'tests/buildbox/backends/koality/test_backend.py:ListBuildsTest.test_simple',
    'tests/buildbox/backends/koality/test_backend.py:SyncBuildDetailsTest.test_simple',
])

TEST_STEP_LABELS = itertools.cycle([
    'tests/buildbox/web/frontend/test_build_list.py',
    'tests/buildbox/web/frontend/test_build_details.py',
    'tests/buildbox/backends/koality/test_backend.py',
    'tests/buildbox/handlers/test_coverage.py',
    'tests/buildbox/handlers/test_xunit.py',
])


def generate_build(session, revision, status=Status.finished, result=Result.passed):
    label = 'D%s: %s' % (random.randint(1000, 100000), revision.message.splitlines()[0])[:128]
    build = Build(
        repository=revision.repository,
        project=project,
        parent_revision=revision,
        status=status,
        result=result,
        label=label,
    )
    session.add(build)

    phase1_setup = Phase(
        repository=build.repository, project=build.project, build=build,
        status=status, result=result, label='Setup',
    )
    session.add(phase1_setup)

    phase1_compile = Phase(
        repository=build.repository, project=build.project, build=build,
        status=status, result=result, label='Compile',
    )
    session.add(phase1_compile)

    phase1_test = Phase(
        repository=build.repository, project=build.project, build=build,
        status=status, result=result, label='Test',
    )
    session.add(phase1_test)

    step = Step(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=status, result=result,
        label=TEST_STEP_LABELS.next(),
    )
    session.add(step)
    step = Step(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=status, result=result,
        label=TEST_STEP_LABELS.next(),
    )
    session.add(step)

    return build


def generate_revision(session, repository, author):
    revision = Revision(
        repository=repository, sha=uuid.uuid4().hex, author=author,
        message='Correct some initial schemas and first draft at some mock datageneration\n\n'
                'https://github.com/dcramer/buildbox/commit/68d1c899e3c821c920ea3baf244943b10ed273b5'
    )
    session.add(revision)

    return revision


def generate_test_results(session, build, result=Result.passed):
    test = Test(
        build=build, project=build.project,
        result=result, label=TEST_LABELS.next(),
        duration=random.randint(0, 3000),
    )
    session.add(test)

    return test


with Backend.instance().get_session() as session:
    repository = Repository(
        url='https://github.com/example/example.git')
    session.add(repository)

    project = Project(
        slug='example', name='example', repository=repository)
    session.add(project)

    author = Author(name='David Cramer', email='dcramer@gmail.com')
    session.add(author)

    # generate a bunch of builds
    for _ in xrange(50):
        result = Result.failed if random.randint(0, 10) > 7 else Result.passed

        revision = generate_revision(session, repository, author)
        session.add(revision)

        build = generate_build(
            session,
            revision=revision,
            result=result,
        )
        for _ in xrange(50):
            generate_test_results(session, build, result)
