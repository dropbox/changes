from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.constants import Status
from changes.models import FileCoverage, Job, Project, Source


class ProjectSourceDetailsAPIView(APIView):
    def get(self, project_id, source_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        context = self.serialize(source)

        if source.patch:
            diff = source.patch.diff
        else:
            vcs = repo.get_vcs()
            if vcs:
                try:
                    diff = vcs.export(source.revision_sha)
                except Exception:
                    diff = None
            else:
                diff = None

        if diff:
            files = self._get_files_from_raw_diff(diff)
            coverage = self._get_coverage_by_source_id(source_id, files)
        else:
            coverage = None

        context['diff'] = diff
        context['coverage'] = coverage

        return self.respond(context)

    def _get_files_from_raw_diff(self, diff):
        files = []
        diff_lines = diff.split('\n')
        for line in diff_lines:
            if line.startswith('+++ b/'):
                files += [unicode(line[6:])]

        return files

    def _get_coverage_by_source_id(self, source_id, files):
        # Grab the newest, finished job_id from the source
        newest_completed_job = Job.query.filter(
            Job.source_id == source_id,
            Job.status == Status.finished,
        ).order_by(Job.date_created.desc()).first()

        # grab the filecoverage for that job and filenames
        all_file_coverages = FileCoverage.query.filter(
            FileCoverage.job_id == newest_completed_job.id,
            FileCoverage.filename.in_(files),
        ).all()

        coverage_dict = {}
        for coverage in all_file_coverages:
            coverage_dict[coverage.filename] = coverage.data

        missed_files = {file for file in files if file not in coverage_dict}

        for file in missed_files:
            coverage_dict[file] = None

        return coverage_dict
