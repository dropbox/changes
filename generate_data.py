#!/usr/bin/env python

import os
import sys

answer = raw_input('This will wipe all data in the `buildbox` database!\nDo you wish to continue? [yN] ').lower()
if answer != 'y':
    sys.exit(1)


assert not os.system('dropdb buildbox')
assert not os.system('createdb -E utf-8 buildbox')
assert not os.system('alembic upgrade head')


import uuid

from buildbox.db.backend import Backend
from buildbox.constants import Status, Result
from buildbox.models import (
    Project, Repository, Author, Revision, Build, Phase, Step
)


with Backend.instance().get_session() as session:
    repo = Repository(
        url='https://github.com/dropbox/buildbox.git')
    session.add(repo)

    project = Project(slug='buildbox', name='buildbox', repository_id=repo.id)
    session.add(project)

    author = Author(name='David Cramer', email='dcramer@gmail.com')
    session.add(author)

    revision = Revision(
        repository_id=repo.id, sha=uuid.uuid4().hex, author_id=author.id,
        message='Correct some initial schemas and first draft at some mock datageneration\n\n'
                'https://github.com/dcramer/buildbox/commit/68d1c899e3c821c920ea3baf244943b10ed273b5'
    )
    session.add(revision)

    build = Build(
        repository_id=repo.id, project_id=project.id, parent_revision_sha=revision.sha,
        status=Status.finished, result=Result.passed, label='D1345',
    )
    session.add(build)

    build2 = Build(
        repository_id=repo.id, project_id=project.id, parent_revision_sha=revision.sha,
        status=Status.inprogress, result=Result.failed, label='D1459',
    )
    session.add(build2)

    phase1_setup = Phase(
        repository_id=repo.id, project_id=project.id, build_id=build.id,
        status=Status.finished, result=Result.passed, label='Setup',
    )
    session.add(phase1_setup)

    phase1_compile = Phase(
        repository_id=repo.id, project_id=project.id, build_id=build.id,
        status=Status.finished, result=Result.passed, label='Compile',
    )
    session.add(phase1_compile)

    phase1_test = Phase(
        repository_id=repo.id, project_id=project.id, build_id=build.id,
        status=Status.finished, result=Result.passed, label='Test',
    )
    session.add(phase1_test)

    phase2_setup = Phase(
        repository_id=repo.id, project_id=project.id, build_id=build2.id,
        status=Status.finished, result=Result.passed, label='Setup',
    )
    session.add(phase2_setup)

    phase2_compile = Phase(
        repository_id=repo.id, project_id=project.id, build_id=build2.id,
        status=Status.finished, result=Result.passed, label='Compile',
    )
    session.add(phase2_compile)

    phase2_test = Phase(
        repository_id=repo.id, project_id=project.id, build_id=build2.id,
        status=Status.inprogress, result=Result.failed, label='Test',
    )
    session.add(phase2_test)

    step = Step(
        repository_id=repo.id, project_id=project.id, build_id=build.id,
        phase_id=phase1_test.id, status=Status.finished, result=Result.passed,
        label='tests/buildbox/web/frontend/test_build_details.py',
    )
    session.add(step)
    step = Step(
        repository_id=repo.id, project_id=project.id, build_id=build.id,
        phase_id=phase1_test.id, status=Status.finished, result=Result.passed,
        label='tests/buildbox/web/frontend/test_build_list.py',
    )
    session.add(step)
    step = Step(
        repository_id=repo.id, project_id=project.id, build_id=build2.id,
        phase_id=phase2_test.id, status=Status.finished, result=Result.failed,
        label='tests/buildbox/web/frontend/test_build_details.py',
    )
    session.add(step)
    step = Step(
        repository_id=repo.id, project_id=project.id, build_id=build2.id,
        phase_id=phase2_test.id, status=Status.inprogress, result=Result.unknown,
        label='tests/buildbox/web/frontend/test_build_list.py',
    )
    session.add(step)
