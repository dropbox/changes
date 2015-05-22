from __future__ import absolute_import, division

from sqlalchemy.sql import func, case

from changes.constants import Result
from changes.models import Build, TestCase, Source, Job
from changes.utils.http import build_uri


def get_flaky_tests(start_period, end_period, projects, maxFlakyTests):
    test_queryset = TestCase.query.join(
        Job, Job.id == TestCase.job_id,
    ).join(
        Build, Build.id == Job.build_id,
    ).filter(
        Build.project_id.in_(p.id for p in projects),
        TestCase.result == Result.passed,
        Build.date_created >= start_period,
        Build.date_created < end_period,
    ).join(
        Source, Source.id == Build.source_id,
    ).filter(
        Source.patch_id == None,  # NOQA
    )

    flaky_test_queryset = test_queryset.with_entities(
        TestCase.name,
        func.sum(case([(TestCase.reruns > 0, 1)], else_=0)).label('reruns'),
        func.count('*').label('count')
    ).group_by(
        TestCase.name
    ).order_by(
        func.sum(TestCase.reruns).desc()
    ).limit(maxFlakyTests)

    flaky_list = []
    for name, reruns, count in flaky_test_queryset:
        if reruns == 0:
            continue

        rerun = test_queryset.filter(
            TestCase.name == name,
            TestCase.reruns > 0,
        ).order_by(
            TestCase.date_created.desc()
        ).first()

        flaky_list.append({
            'id': rerun.id,
            'name': name,
            'short_name': rerun.short_name,
            'package': rerun.package,
            'hash': rerun.name_sha,
            'project_id': rerun.project_id,
            'flaky_runs': reruns,
            'passing_runs': count,
            'link': build_uri('/projects/{0}/builds/{1}/jobs/{2}/logs/{3}/'.format(
                rerun.project.slug,
                rerun.job.build.id.hex,
                rerun.job.id.hex,
                rerun.step.logsources[0].id.hex)),
        })

    return flaky_list
