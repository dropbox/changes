import os
os.system('dropdb buildbox')
os.system('createdb -E utf-8 buildbox')
os.system('alembic upgrade head')

import uuid

from buildbox.db.backend import Backend
from buildbox.constants import Status, Result
from buildbox.models import (
    Project, Repository, Author, Revision, Build
)


session = Backend.instance().get_session()

repo = Repository(
    url='https://github.com/dropbox/buildbox.git')
session.add(repo)
session.commit()

project = Project(name='buildbox', repository_id=repo.id)
session.add(project)
session.commit()

author = Author(name='David Cramer', email='dcramer@gmail.com')
session.add(author)
session.commit()

revision = Revision(
    repository_id=repo.id, sha=uuid.uuid4().hex, author_id=author.id,
    message='Correct some initial schemas and first draft at some mock datageneration\n\n'
            'https://github.com/dcramer/buildbox/commit/68d1c899e3c821c920ea3baf244943b10ed273b5'
)
session.add(revision)
session.commit()

build = Build(
    repository_id=repo.id, project_id=project.id, parent_revision_sha=revision.sha,
    status=Status.finished, result=Result.passed, label='D1345',
)
session.add(build)
session.commit()

build = Build(
    repository_id=repo.id, project_id=project.id, parent_revision_sha=revision.sha,
    status=Status.inprogress, result=Result.failed, label='D1459',
)
session.add(build)
session.commit()
