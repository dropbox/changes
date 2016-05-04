from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

import uuid

from changes.api.base import APIView, error
from changes.config import db
from changes.constants import Result, Status
from changes.models.build import Build
from changes.models.job import Job
from changes.models.project import Project, ProjectOption
from changes.models.source import Source
from changes.models.test import TestCase
from changes.utils.trees import build_tree


class ProjectTestGroupIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('parent', type=unicode, location='args')
    parser.add_argument('build_id', type=uuid.UUID, location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        if args.build_id:
            build = Build.query.get(args.build_id)
            if not build:
                return error("Build not found", http_code=404)
        else:
            latest_build = Build.query.join(
                Source, Source.id == Build.source_id,
            ).filter(
                Source.patch_id == None,    # NOQA
                Build.project_id == project.id,
                Build.result == Result.passed,
                Build.status == Status.finished,
            ).order_by(
                Build.date_created.desc(),
            ).limit(1).first()

            if not latest_build:
                return self.respond({})
            build = latest_build

        return self.respond(_generate_testgroup_data(build, project.id, args.parent))


def _generate_testgroup_data(build, project_id, parent=None):
    job_list = db.session.query(Job.id).filter(
        Job.build_id == build.id,
    )

    if job_list:
        # use the most recent test
        test_list = db.session.query(
            TestCase.name, TestCase.duration, TestCase.id
        ).filter(
            TestCase.job_id.in_(job_list),
        )
        if parent:
            test_list = test_list.filter(
                TestCase.name.startswith(parent),
            )
        test_list = list(test_list)
    else:
        test_list = []

    if test_list:
        sep = TestCase(name=test_list[0][0]).sep

        groups = build_tree(
            [t[0] for t in test_list],
            sep=sep,
            min_children=1,
            parent=parent,
        )

        results = []
        for group in groups:
            num_tests = 0
            total_duration = 0
            test_id = None
            for name, duration, tid in test_list:
                if name == group or name.startswith(group + sep):
                    num_tests += 1
                    total_duration += duration
                    test_id = tid

            if parent:
                name = group[len(parent) + len(sep):]
            else:
                name = group
            data = {
                'name': name,
                'path': group,
                'totalDuration': total_duration,
                'numTests': num_tests,
            }
            if num_tests == 1:
                data['id'] = test_id
            results.append(data)
        results.sort(key=lambda x: x['totalDuration'], reverse=True)

        trail = []
        context = []
        if parent:
            for chunk in parent.split(sep):
                context.append(chunk)
                trail.append({
                    'path': sep.join(context),
                    'name': chunk,
                })
    else:
        results = []
        trail = []

    options = dict(
        (o.name, o.value) for o in ProjectOption.query.filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name == 'build.test-duration-warning',
        )
    )

    over_threshold_duration = options.get('build.test-duration-warning')
    if over_threshold_duration:
        over_threshold_count = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.job_id.in_(job_list),
            TestCase.duration >= over_threshold_duration,
        ).count()
    else:
        over_threshold_count = 0

    return {
        'groups': results,
        'trail': trail,
        'overThreshold': {
            'count': over_threshold_count,
            'duration': over_threshold_duration,
        }
    }
