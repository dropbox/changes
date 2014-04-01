from __future__ import absolute_import, print_function

from changes.constants import Result, Status
from changes.models import Job, JobStep, TestGroup, LogSource, LogChunk, Source

UNSET = object()


class NotificationHandler(object):
    def get_test_failures(self, job):
        return TestGroup.query.filter(
            TestGroup.job_id == job.id,
            TestGroup.result == Result.failed,
            TestGroup.num_leaves == 0,
        ).order_by(TestGroup.name.asc())

    def get_parent(self, job):
        return Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Source.revision_sha != job.build.source.revision_sha,
            Job.project == job.project,
            Job.date_created < job.date_created,
            Job.status == Status.finished,
            Job.result.in_([Result.passed, Result.failed]),
        ).order_by(Job.date_created.desc()).first()

    def get_primary_log_source(self, job):
        primary_log = LogSource.query.filter(
            LogSource.job_id == job.id,
        ).join(
            JobStep, LogSource.step_id == JobStep.id,
        ).filter(
            JobStep.result == Result.failed,
        ).order_by(JobStep.date_finished).first()
        if primary_log:
            return primary_log

        primary_log = LogSource.query.filter(
            LogSource.job_id == job.id,
        ).order_by(LogSource.date_created.asc()).first()

        return primary_log

    def should_notify(self, job, parent=UNSET):
        """
        Compare with parent job (previous job) and confirm if current
        job provided any change in state (e.g. new failures).
        """
        if job.result not in (Result.failed, Result.passed):
            return

        if parent is UNSET:
            parent = self.get_parent(job)

        # if theres no parent, this job must be at fault
        if parent is None:
            return job.result == Result.failed

        if job.result == Result.passed == parent.result:
            return False

        current_failures = set([t.name_sha for t in self.get_test_failures(job)])
        # if we dont have any testgroup failures, then we cannot identify the cause
        # so we must notify the individual
        if not current_failures:
            return True

        parent_failures = set([t.name_sha for t in self.get_test_failures(parent)])
        if parent_failures != current_failures:
            return True

        return False

    def get_log_clipping(self, logsource, max_size=5000, max_lines=25):
        queryset = LogChunk.query.filter(
            LogChunk.source_id == logsource.id,
        )
        tail = queryset.order_by(LogChunk.offset.desc()).limit(1).first()

        chunks = list(queryset.filter(
            (LogChunk.offset + LogChunk.size) >= max(tail.offset - max_size, 0),
        ).order_by(LogChunk.offset.asc()))

        clipping = ''.join(l.text for l in chunks).strip()[-max_size:]
        # only return the last 25 lines
        clipping = '\r\n'.join(clipping.splitlines()[-max_lines:])

        return clipping

    def get_result_label(self, job, parent):
        if parent:
            if parent.result == Result.failed and job.result == Result.passed:
                result_label = u'Fixed'
            else:
                result_label = unicode(job.result)
        else:
            result_label = unicode(job.result)

        return result_label

    def job_finished_handler(self, job, **kwargs):
        parent = self.get_parent(job)

        if not self.should_notify(job, parent):
            return

        self.send(job, parent)

    def send(self, job, parent):
        raise NotImplementedError
