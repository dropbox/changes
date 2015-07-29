from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Repository, Project, TestCase, Job, Source


class HistorySliceable(object):
    """Fake sliceable object to make APIView#paginate happy

    APIView#paginate wants an "infinite" iterable, from which it then will
    slice the section which it cares about. Unfortunately, because we require
    the git log output to sort the iterable, it is not feasible to log the
    entire history, fetch its data, sort it, and then pass it to paginate
    which will only slice out a small section. The old solution was to fetch
    "more than we need" while still not being infinite; unfortunately, we
    always could want to paginate more, so that's not a good solution since
    it arbitrarily cut off pagination.

    This works around the problem by passing a `HistorySliceable` object to
    APIView#paginate. When paginate slices this, we then on-demand fetch
    the relevant commits from git and from the database and sort/prepare them.

    This should allow infinite pagination.
    """
    def __init__(self, project_id, branch, test, repository_id, serialize):
        self.project_id = project_id
        self.branch = branch
        self.test = test
        self.repository_id = repository_id
        self.serialize = serialize

    def __getitem__(self, sliced):

        repo = Repository.query.get(self.repository_id)
        vcs = repo.get_vcs()

        log = vcs.log(offset=sliced.start, limit=sliced.stop - sliced.start, branch=self.branch)

        revs = [rev.id for rev in log]
        if revs == []:
            return []

        # restrict the join to the last N jobs otherwise this can get
        # significantly expensive as we have to seek quite a ways
        recent_runs = list(TestCase.query.options(
            joinedload('job.build'),
            joinedload('job.build.author'),
            joinedload('job.build.source'),
            joinedload('job.build.source.revision'),
        ).filter(
            # join filters
            TestCase.job_id == Job.id,
            Job.source_id == Source.id,
            # other filters
            Job.project_id == self.project_id,
            Source.patch_id == None,  # NOQA
            Source.revision_sha.in_(revs),
            TestCase.name_sha == self.test.name_sha,
        ))

        # Sort by date created; this ensures the runs that end up in
        # recent_runs_map are always the latest run for any given sha
        recent_runs.sort(key=lambda run: run.date_created)
        recent_runs_map = {
            recent_run.job.build.source.revision_sha: recent_run
            for recent_run in recent_runs
        }

        recent_runs = map(recent_runs_map.get, revs)

        jobs = set(r.job for r in recent_runs if r)
        builds = set(j.build for j in jobs)

        serialized_jobs = dict(zip(jobs, self.serialize(jobs)))
        serialized_builds = dict(zip(builds, self.serialize(builds)))

        results = []

        for recent_run in recent_runs:
            if recent_run is not None:
                s_recent_run = self.serialize(recent_run)
                s_recent_run['job'] = serialized_jobs[recent_run.job]
                s_recent_run['job']['build'] = serialized_builds[recent_run.job.build]
                results.append(s_recent_run)
            else:
                results.append(None)

        return results


class ProjectTestHistoryAPIView(APIView):
    get_parser = reqparse.RequestParser()

    get_parser.add_argument('branch', type=str, location='args',
                            default="master")

    def get(self, project_id, test_hash):
        project = Project.get(project_id)
        if not project:
            return '', 404

        # use the most recent test run to find basic details
        test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.desc()).limit(1).first()
        if not test:
            return '', 404

        args = self.get_parser.parse_args()

        return self.paginate(
            HistorySliceable(project_id, args.branch, test, project.repository_id, self.serialize),
            serialize=False
        )
