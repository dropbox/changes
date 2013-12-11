from __future__ import absolute_import, division, unicode_literals

from flask import Response
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, subqueryload

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithBuildSerializer
from changes.api.serializer.models.aggregatetestgroup import AggregateTestGroupWithBuildSerializer
from changes.config import db
from changes.constants import Status
from changes.models import Project, AggregateTestGroup, TestGroup, Build


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

        queryset = db.session.query(AggregateTestGroup, TestGroup).options(
            subqueryload(AggregateTestGroup.first_build),
            subqueryload(AggregateTestGroup.last_build),
            subqueryload(AggregateTestGroup.parent),
            subqueryload('first_build.author'),
            subqueryload('last_build.author'),
        ).join(TestGroup, and_(
            TestGroup.build_id == AggregateTestGroup.last_build_id,
            TestGroup.name_sha == AggregateTestGroup.name_sha,
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

        previous_runs = list(TestGroup.query.filter(
            Build.patch_id == None,  # NOQA
            Build.revision_sha != None,  # NOQA
            Build.status == Status.finished,
            TestGroup.name_sha == test.name_sha,
            TestGroup.project_id == test.project_id,
        ).join(Build).order_by(Build.date_created.desc())[:25])

        # O(N) db calls, so dont abuse it
        context = []
        parent = test
        while parent:
            context.append(parent)
            parent = parent.parent
        context.reverse()

        extended_serializers = {
            TestGroup: TestGroupWithBuildSerializer(),
        }

        context = {
            'test': self.serialize(test, {
                AggregateTestGroup: AggregateTestGroupWithBuildSerializer(),
            }),
            'childTests': self.serialize(test_list, {
                AggregateTestGroup: AggregateTestGroupWithBuildSerializer(),
            }),
            'context': context,
            'previousRuns': self.serialize(previous_runs, extended_serializers),
        }

        return self.respond(context)
