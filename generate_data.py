#!/usr/bin/env python

import os
import sys

answer = raw_input('This will wipe all data in the `buildbox` database!\nDo you wish to continue? [yN] ').lower()
if answer != 'y':
    sys.exit(1)


assert not os.system('dropdb buildbox')
assert not os.system('createdb -E utf-8 buildbox')
assert not os.system('alembic upgrade head')


import random
import uuid

from buildbox.db.backend import Backend
from buildbox.constants import Status, Result
from buildbox.models import (
    Project, Repository, Author, Revision, Build, Phase, Step
)


def generate_build(session, revision, status=Status.finished, result=Result.passed):
    build = Build(
        repository=revision.repository,
        project=project,
        parent_revision=revision,
        status=status,
        result=result,
        label='D%s' % (random.randint(1000, 100000)),
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
        label='tests/buildbox/web/frontend/test_build_details.py',
    )
    session.add(step)
    step = Step(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=status, result=result,
        label='tests/buildbox/web/frontend/test_build_list.py',
    )
    session.add(step)

    return build


with Backend.instance().get_session() as session:
    repo = Repository(
        url='https://github.com/dropbox/buildbox.git')
    session.add(repo)

    project = Project(slug='buildbox', name='buildbox', repository=repo)
    session.add(project)

    author = Author(name='David Cramer', email='dcramer@gmail.com')
    session.add(author)

    revision = Revision(
        repository=repo, sha=uuid.uuid4().hex, author=author,
        message='Correct some initial schemas and first draft at some mock datageneration\n\n'
                'https://github.com/dcramer/buildbox/commit/68d1c899e3c821c920ea3baf244943b10ed273b5'
    )
    session.add(revision)

    # generate a bunch of builds
    for _ in xrange(50):
        generate_build(
            session,
            revision=revision,
            result=Result.failed if random.randint(0, 10) > 7 else Result.passed,
        )
