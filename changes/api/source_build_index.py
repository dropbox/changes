from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Source, Job


class SourceBuildIndexAPIView(APIView):
    def get(self, source_id):
        source = Source.query.filter(
            Source.id == source_id,
        ).first()
        if source is None:
            return '', 404

        builds = self.serialize(list(
            Build.query.options(
                joinedload('author')
            ).filter(
                Build.source_id == source.id,
                Build.id == Job.build_id
            ).order_by(Build.date_created.desc())
        ))
        build_ids = [build['id'] for build in builds]

        jobs = self.serialize(list(Job.query.filter(
            Job.build_id.in_(build_ids)
        )))

        for b in builds:
            b['jobs'] = [j for j in jobs if j['build']['id'] == b['id']]

        return self.paginate(builds, serialize=False)
