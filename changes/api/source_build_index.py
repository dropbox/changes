from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser

from sqlalchemy.orm import joinedload
from uuid import UUID

from changes.api.base import APIView, error
from changes.models.build import Build
from changes.models.job import Job
from changes.models.source import Source


class SourceBuildIndexAPIView(APIView):
    """
    Gets all the builds for a given source object
    """

    get_parser = RequestParser()
    get_parser.add_argument('source_id', type=UUID, location='args')
    get_parser.add_argument('revision_sha', location='args')
    get_parser.add_argument('repo_id', type=UUID, location='args')

    def get(self):
        args = self.get_parser.parse_args()
        # this can take either a source id or a revision/repo id. For the
        # latter, only non-patch sources are looked at
        source_id = args.source_id
        revision_sha = args.revision_sha
        repo_id = args.repo_id

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
            return error('invalid args')

        if source is None:
            return error("source not found", http_code=404)

        builds = self.serialize(list(
            Build.query.options(
                joinedload('author')
            ).filter(
                Build.source_id == source.id,
            ).order_by(Build.date_created.desc())
        ))
        build_ids = [build['id'] for build in builds]

        if len(builds) > 0:
            jobs = self.serialize(list(Job.query.filter(
                Job.build_id.in_(build_ids)
            )))

            for b in builds:
                b['jobs'] = [j for j in jobs if j['build']['id'] == b['id']]

        return self.paginate(builds, serialize=False)
