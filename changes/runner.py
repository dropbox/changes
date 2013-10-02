#!/usr/bin/env python


def web():
    from gevent import wsgi
    from changes.config import create_app

    print "Listening on http://0.0.0.0:5000"

    app = create_app()
    wsgi.WSGIServer(('0.0.0.0', 5000), app).serve_forever()


def poller():
    import time
    from changes.config import create_app, db
    from changes.backends.phabricator.poller import PhabricatorPoller
    from phabricator import Phabricator

    app = create_app()
    app_context = app.app_context()
    app_context.push()

    from changes.models import (
        RemoteEntity, EntityType, Project, Repository
    )

    try:
        RemoteEntity.query.filter_by(
            provider='phabricator',
            remote_id='Server',
            type=EntityType.project,
        )[0]
    except IndexError:
        repo = Repository(
            url='http://example.com/server',
        )
        db.session.add(repo)
        project = Project(
            repository=repo,
            name='Server',
        )
        db.session.add(project)
        entity = RemoteEntity(
            provider='phabricator',
            remote_id='Server',
            internal_id=project.id,
            type=EntityType.project,
        )
        db.session.add(entity)

    print "Polling for changes"
    client = Phabricator(host='https://tails.corp.dropbox.com/api/')
    poller = PhabricatorPoller(client)
    poller._populate_project_cache()
    while True:
        for project, revision in poller._yield_revisions():
            poller.sync_revision(project, revision)
            db.session.commit()
        time.sleep(5)
