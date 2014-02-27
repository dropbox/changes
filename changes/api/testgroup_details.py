from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithJobSerializer
from changes.constants import Status, NUM_PREVIOUS_RUNS
from changes.models import Job, TestGroup, TestCase, Source


class TestGroupDetailsAPIView(APIView):
    def get(self, testgroup_id):
        testgroup = TestGroup.query.get(testgroup_id)
        if testgroup is None:
            return '', 404

        child_testgroups = list(TestGroup.query.filter(
            TestGroup.parent_id == testgroup.id,
        ))
        for tg in child_testgroups:
            tg.parent = testgroup

        if child_testgroups:
            test_case = None
        else:
            # we make the assumption that if theres no child testgroups, then
            # there should be a single test case
            test_case = TestCase.query.filter(
                TestCase.groups.contains(testgroup),
            ).first()

        job = testgroup.job

        # limit previous runs to last 1000 jobs
        job_sq = Job.query.filter(
            Job.project == job.project,
            Job.date_created < job.date_created,
            Job.status == Status.finished,
        ).join(
            Source, Job.source_id == Source.id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Source.revision_sha != None,  # NOQA
        ).order_by(Job.date_created.desc()).limit(1000).subquery()

        previous_runs = list(TestGroup.query.options(
            contains_eager('job', alias=job_sq),
            contains_eager('job.source'),
            joinedload('parent'),
            joinedload('job', 'build'),
        ).join(
            job_sq, TestGroup.job_id == job_sq.c.id,
        ).filter(
            TestGroup.name_sha == testgroup.name_sha,
        ).order_by(job_sq.c.date_created.desc())[:NUM_PREVIOUS_RUNS])

        extended_serializers = {
            TestGroup: TestGroupWithJobSerializer(),
        }

        # O(N) db calls, so dont abuse it
        context = []
        parent = testgroup
        while parent:
            context.append(parent)
            parent = parent.parent
        context.reverse()

        context = {
            'project': testgroup.project,
            'build': testgroup.job.build,
            'job': testgroup.job,
            'testGroup': testgroup,
            'childTestGroups': child_testgroups,
            'context': context,
            'testCase': test_case,
            'previousRuns': self.serialize(previous_runs, extended_serializers),
        }

        return self.respond(context)
