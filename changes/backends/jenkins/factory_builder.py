from __future__ import absolute_import, division

import re

from datetime import datetime

from changes.config import db
from changes.constants import Status
from changes.db.utils import get_or_create, create_or_update
from changes.models import TestResultManager, Node, JobPhase, JobStep
from changes.utils.agg import safe_agg

from .builder import JenkinsBuilder, NotFound, RESULT_MAP

BASE_XPATH = '/freeStyleProject/build[action/cause/upstreamProject="{upstream_job}" and action/cause/upstreamBuild="{build_no}"]/number'
DOWNSTREAM_XML_RE = re.compile(r'<number>(\d+)</number>')


class JenkinsFactoryBuilder(JenkinsBuilder):
    provider = 'jenkins'

    def __init__(self, *args, **kwargs):
        self.downstream_job_names = kwargs.pop('downstream_job_names', ())
        super(JenkinsFactoryBuilder, self).__init__(*args, **kwargs)

    def _get_downstream_jobs(self, job, downstream_job_name):
        xpath = BASE_XPATH.format(
            upstream_job=job.data['job_name'],
            build_no=job.data['build_no']
        )
        response = self._get_raw_response('/job/{job_name}/api/xml/'.format(
            job_name=downstream_job_name,
        ), params={
            'depth': 1,
            'xpath': xpath,
            'wrapper': 'a',
        })
        if not response:
            return []

        return map(int, DOWNSTREAM_XML_RE.findall(response))

    def _sync_downstream_job(self, phase, job_name, build_no):
        item = self._get_response('/job/{}/{}'.format(
            job_name, build_no))

        node, _ = get_or_create(Node, where={
            'label': item['builtOn'],
        })

        values = {
            'date_started': datetime.utcfromtimestamp(
                item['timestamp'] / 1000),
        }
        if item['building']:
            values['status'] = Status.in_progress
        else:
            values['status'] = Status.finished
            values['result'] = RESULT_MAP[item['result']]
            # values['duration'] = item['duration'] or None
            values['date_finished'] = datetime.utcfromtimestamp(
                (item['timestamp'] + item['duration']) / 1000)

        jobstep, created = create_or_update(JobStep, where={
            'phase': phase,
            'label': item['fullDisplayName'],
            'job_id': phase.job_id,
            'project_id': phase.project_id,
            'node_id': node.id,
            'data': {
                'job_name': job_name,
                'queued': False,
                'item_id': None,
                'build_no': build_no,
            },
        }, values=values)

        if 'backend' not in jobstep.data:
            jobstep.data.update({
                'backend': {
                    'uri': item['url'],
                    'label': item['fullDisplayName'],
                }
            })
            db.session.add(jobstep)

        return jobstep

    def _sync_test_results(self, job):
        # sync any upstream results we may have collected
        try:
            test_report = self._get_response('/job/{job_name}/{build_no}/testReport/'.format(
                job_name=job.data['job_name'],
                build_no=job.data['build_no'],
            ))
        except NotFound:
            test_list = []
        else:
            test_list = self._process_test_report(job, test_report)

        # for any downstream jobs, pull their results using xpath magic
        for downstream_job_name in self.downstream_job_names:
            # XXX(dcramer): this is kind of gross, as we create the phase first
            # so we have an ID to reference, and then we update it with the
            # collective stats
            jobphase, created = get_or_create(JobPhase, where={
                'job': job,
                'label': downstream_job_name,
            }, defaults={
                'status': job.status,
                'result': job.result,
                'project_id': job.project_id,
            })
            jobsteps = []

            for build_no in self._get_downstream_jobs(job, downstream_job_name):
                try:
                    # XXX(dcramer): ideally we would grab this with the first query
                    # but because we dont want to rely on an XML parser, we're doing
                    # a second http request for build details
                    jobsteps.append(self._sync_downstream_job(
                        jobphase, downstream_job_name, build_no))

                    test_report = self._get_response('/job/{job_name}/{build_no}/testReport/'.format(
                        job_name=downstream_job_name,
                        build_no=build_no,
                    ))
                except NotFound:
                    pass
                else:
                    test_list.extend(self._process_test_report(job, test_report))

            if jobsteps:
                # update phase statistics
                jobphase.date_started = safe_agg(
                    min, (s.date_started for s in jobsteps), default=job.date_started)
                jobphase.date_finished = safe_agg(
                    max, (s.date_finished for s in jobsteps), default=job.date_finished)
                # jobphase.duration = (jobphase.date_finished - jobphase.date_started).total_seconds()
            else:
                jobphase.date_started = job.date_started
                jobphase.date_finished = job.date_finished
            db.session.add(jobphase)

        manager = TestResultManager(job)
        with db.session.begin_nested():
            manager.save(test_list)
