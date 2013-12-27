from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from flask import Response
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, subqueryload

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithJobSerializer
from changes.api.serializer.models.aggregatetestgroup import AggregateTestGroupWithJobSerializer
from changes.config import db
from changes.constants import Status
from changes.models import Project, AggregateTestGroup, TestGroup, Job


class ProjectTestDetailsAPIView(APIView):
    def _get_project(self, project_id):
        queryset = Project.query.options(
            joinedload(Project.repository),
        )

        project = queryset.filter_by(slug=project_id).first()
        if project is None:
            project = queryset.get(project_id)
        return project

    def get(self, project_id, test_id):
        project = self._get_project(project_id)
        if not project:
            return Response(status=404)

        cutoff = datetime.utcnow() - timedelta(days=3)

        queryset = db.session.query(AggregateTestGroup, TestGroup).options(
            subqueryload(AggregateTestGroup.first_job),
            subqueryload(AggregateTestGroup.last_job),
            subqueryload(AggregateTestGroup.parent),
            subqueryload('first_job.author'),
            subqueryload('last_job.author'),
        ).join(
            AggregateTestGroup.last_job,
        ).join(TestGroup, and_(
            TestGroup.job_id == AggregateTestGroup.last_job_id,
            TestGroup.name_sha == AggregateTestGroup.name_sha,
            Job.date_created > cutoff,
        )).order_by(TestGroup.duration.desc())

        result = queryset.filter(
            AggregateTestGroup.id == test_id,
        ).first()
        if result is None:
            return Response(status=404)

        test, lastgroup = result

        test.last_testgroup = lastgroup

        test_results = list(queryset.filter(
            AggregateTestGroup.parent_id == test.id,
            AggregateTestGroup.project_id == project.id,
        ))
        test_list = []
        for agg, group in test_results:
            agg.last_testgroup = group
            test_list.append(agg)

        previous_runs = list(TestGroup.query.options(
            joinedload('job'),
            joinedload('job.author'),
        ).filter(
            Job.patch_id == None,  # NOQA
            Job.revision_sha != None,  # NOQA
            Job.status == Status.finished,
            TestGroup.name_sha == test.name_sha,
            TestGroup.project_id == test.project_id,
        ).join(Job).order_by(Job.date_created.desc())[:25])

        # O(N) db calls, so dont abuse it
        context = []
        parent = test
        while parent:
            context.append(parent)
            parent = parent.parent
        context.reverse()

        extended_serializers = {
            TestGroup: TestGroupWithJobSerializer(),
        }

        context = {
            'test': self.serialize(test, {
                AggregateTestGroup: AggregateTestGroupWithJobSerializer(),
            }),
            'childTests': self.serialize(test_list, {
                AggregateTestGroup: AggregateTestGroupWithJobSerializer(),
            }),
            'context': context,
            'previousRuns': self.serialize(previous_runs, extended_serializers),
        }

        return self.respond(context)
