from __future__ import absolute_import, division

from sqlalchemy.sql import func, case

from changes.constants import Result
from changes.models.build import Build
from changes.models.job import Job
from changes.models.source import Source
from changes.models.test import TestCase
from changes.utils.http import build_uri


def get_flaky_tests(start_period, end_period, projects, maxFlakyTests):
    test_queryset = TestCase.query.filter(
        TestCase.project_id.in_(p.id for p in projects),
        TestCase.result == Result.passed,
        TestCase.date_created >= start_period,
        TestCase.date_created < end_period,
    ).join(
        Job, Job.id == TestCase.job_id,
    ).join(
        Build, Build.id == Job.build_id,
    ).join(
        Source, Source.id == Build.source_id,
    ).filter(
        Source.patch_id == None,  # NOQA
    )

    flaky_test_queryset = test_queryset.with_entities(
        TestCase.name_sha,
        TestCase.project_id,
        func.sum(case([(TestCase.reruns > 0, 1)], else_=0)).label('reruns'),
        func.sum(case([(TestCase.reruns > 1, 1)], else_=0)).label('double_reruns'),
        func.count('*').label('count')
    ).group_by(
        TestCase.name_sha,
        TestCase.project_id
    ).order_by(
        func.sum(TestCase.reruns).desc()
    ).limit(maxFlakyTests)

    project_names = {p.id: p.name for p in projects}

    flaky_list = []
    for name_sha, project_id, reruns, double_reruns, count in flaky_test_queryset:
        if reruns == 0:
            continue

        rerun = test_queryset.filter(
            TestCase.name_sha == name_sha,
            TestCase.project_id == project_id,
            TestCase.reruns > 0,
        ).order_by(
            TestCase.date_created.desc()
        ).first()

        flaky_list.append({
            'id': rerun.id,
            'name': rerun.name,
            'short_name': rerun.short_name,
            'package': rerun.package,
            'hash': name_sha,
            'project_id': rerun.project_id,
            'project_name': project_names[rerun.project_id],
            'flaky_runs': reruns,
            'double_reruns': double_reruns,
            'passing_runs': count,
            'link': build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
                rerun.project.slug,
                rerun.job.build.id.hex,
                rerun.job.id.hex,
                rerun.id.hex)),
        })

    return flaky_list
