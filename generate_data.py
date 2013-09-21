from buildbox.db.backend import Backend
from buildbox.models import (
    Project, Repository, Author, Revision, Build, BuildStatus)


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
    repository_id=repo.id, author_id=author.id, sha='a' * 40,
    message='This is a commit message')
session.add(revision)
session.commit()

build = Build(
    repository_id=repo.id, project_id=project.id, parent_revision_id=revision.id,
    status=BuildStatus.PASSED,
)
session.add(build)
session.commit()

build = Build(
    repository_id=repo.id, project_id=project.id, parent_revision_id=revision.id,
    status=BuildStatus.FAILED,
)
session.add(build)
session.commit()
