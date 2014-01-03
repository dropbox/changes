from __future__ import absolute_import, division

import re

from changes.config import db
from changes.models import TestResultManager

from .builder import JenkinsBuilder, NotFound

BASE_XPATH = '/freeStyleProject/build[action/cause/upstreamProject=%22{upstream_job}%22%20and%20action/cause/upstreamBuild={build_no}]/number'
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
        response = self._get_raw_response('/job/{job_name}/api/xml/?depth=1&xpath={xpath}&wrapper=a'.format(
            job_name=downstream_job_name,
            xpath=xpath,
        ))
        if not response:
            return []

        return map(int, DOWNSTREAM_XML_RE.findall(response))

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
            for build_no in self._get_downstream_jobs(job, downstream_job_name):
                try:
                    test_report = self._get_response('/job/{job_name}/{build_no}/testReport/'.format(
                        job_name=downstream_job_name,
                        build_no=build_no,
                    ))
                except NotFound:
                    pass
                else:
                    test_list.extend(self._process_test_report(job, test_report))

        manager = TestResultManager(job)
        with db.session.begin_nested():
            manager.save(test_list)
