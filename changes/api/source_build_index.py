from __future__ import absolute_import, division, unicode_literals

from flask import request

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Source, Job


class SourceBuildIndexAPIView(APIView):
    """
    Gets all the builds for a given source object
    """

    def get(self):
        # this can take either a source id or a revision/repo id. For the
        # latter, only non-patch sources are looked at
        source_id = request.args.get('source_id')
        revision_sha = request.args.get('revision_sha')
        repo_id = request.args.get('repo_id')

        if source_id:
            source = Source.query.filter(
                Source.id == source_id,
            ).first()
        elif revision_sha and repo_id:
            source = Source.query.filter(
                Source.revision_sha == revision_sha,
                Source.repository_id == repo_id,
                Source.patch_id == None  # NOQA
            ).first()
        else:
            return 'invalid args', 400

        if source is None:
            return '', 404

        builds = self.serialize(list(
            Build.query.options(
                joinedload('author')
            ).filter(
                Build.source_id == source.id,
            ).order_by(Build.date_created.desc())
        ))
        build_ids = [build['id'] for build in builds]

        jobs = self.serialize(list(Job.query.filter(
            Job.build_id.in_(build_ids)
        )))

        for b in builds:
            b['jobs'] = [j for j in jobs if j['build']['id'] == b['id']]

        return self.paginate(builds, serialize=False)
