from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.constants import Result, Status
from changes.models import Project, TestCase, Job, Source


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

        latest_job = Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Job.project_id == project.id,
            Job.result == Result.passed,
            Job.status == Status.finished,
        ).order_by(
            Job.date_created.desc(),
        ).limit(1).first()

        if not latest_job:
            return self.respond([])

        # use the most recent test
        test_list = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.job_id == latest_job.id,
        )

        if args.min_duration:
            test_list = test_list.filter(
                TestCase.duration >= args.min_duration,
            )

        if args.query:
            test_list = test_list.filter(
                TestCase.name.startswith(args.query),
            )

        if args.sort == 'duration':
            sort_by = TestCase.duration.desc()
        elif args.sort == 'name':
            sort_by = TestCase.name.asc()

        test_list = test_list.order_by(sort_by)

        return self.paginate(test_list, serializers={
            TestCase: GeneralizedTestCase(),
        })
