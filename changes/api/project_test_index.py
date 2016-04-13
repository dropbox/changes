from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Project, TestCase, Job, Source


SORT_CHOICES = (
    'duration',
    'name',
)


class ProjectTestIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('min_duration', type=int, location='args')
    parser.add_argument('query', type=unicode, location='args')
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='duration')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_build = Build.query.join(
            Source, Source.id == Build.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project_id == project.id,
            Build.result == Result.passed,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
        ).limit(1).first()

        if not latest_build:
            return self.respond([])

        job_list = db.session.query(Job.id).filter(
            Job.build_id == latest_build.id,
        )

        if not job_list:
            return self.respond([])

        # use the most recent test
        test_list = TestCase.query.filter(
            TestCase.project_id == project.id,
            TestCase.job_id.in_(job_list),
        )

        if args.min_duration:
            test_list = test_list.filter(
                TestCase.duration >= args.min_duration,
            )

        if args.query:
            test_list = test_list.filter(
                TestCase.name.contains(args.query),
            )

        if args.sort == 'duration':
            sort_by = TestCase.duration.desc()
        elif args.sort == 'name':
            sort_by = TestCase.name.asc()

        test_list = test_list.order_by(sort_by)

        return self.paginate(test_list, serializers={
            TestCase: GeneralizedTestCase(),
        })
