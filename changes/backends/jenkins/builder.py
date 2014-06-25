from __future__ import absolute_import, division

import json
import logging
import re
import requests
import time

from cStringIO import StringIO
from contextlib import closing
from datetime import datetime
from flask import current_app
from lxml import etree, objectify

from changes.backends.base import BaseBackend, UnrecoverableException
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import create_or_update, get_or_create
from changes.jobs.sync_artifact import sync_artifact
from changes.jobs.sync_job_step import sync_job_step
from changes.models import (
    Artifact, Cluster, ClusterNode, TestResult,
    LogSource, LogChunk, Node, JobPhase, JobStep
)
from changes.handlers.coverage import CoverageHandler
from changes.handlers.xunit import XunitHandler
from changes.utils.http import build_uri

LOG_CHUNK_SIZE = 4096

RESULT_MAP = {
    'SUCCESS': Result.passed,
    'ABORTED': Result.aborted,
    'FAILURE': Result.failed,
    'REGRESSION': Result.failed,
    'UNSTABLE': Result.failed,
}

QUEUE_ID_XPATH = '/queue/item[action/parameter/name="CHANGES_BID" and action/parameter/value="{job_id}"]/id'
BUILD_ID_XPATH = '/freeStyleProject/build[action/parameter/name="CHANGES_BID" and action/parameter/value="{job_id}"]/number'

XUNIT_FILENAMES = ('junit.xml', 'xunit.xml', 'nosetests.xml')
COVERAGE_FILENAMES = ('coverage.xml',)

ID_XML_RE = re.compile(r'<id>(\d+)</id>')


def chunked(iterator, chunk_size):
    """
    Given an iterator, chunk it up into ~chunk_size, but be aware of newline
    termination as an intended goal.
    """
    result = ''
    for chunk in iterator:
        result += chunk
        while len(result) >= chunk_size:
            newline_pos = result.rfind('\n', 0, chunk_size)
            if newline_pos == -1:
                newline_pos = chunk_size
            else:
                newline_pos += 1
            yield result[:newline_pos]
            result = result[newline_pos:]
    if result:
        yield result


class NotFound(Exception):
    pass


class JenkinsBuilder(BaseBackend):
    provider = 'jenkins'

    def __init__(self, base_url=None, job_name=None, token=None, auth=None,
                 sync_phase_artifacts=True, *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['JENKINS_URL']
        self.token = token or self.app.config['JENKINS_TOKEN']
        self.auth = auth or self.app.config['JENKINS_AUTH']
        self.logger = logging.getLogger('jenkins')
        self.job_name = job_name
        # disabled by default as it's expensive
        self.sync_phase_artifacts = sync_phase_artifacts
        self.sync_log_artifacts = self.app.config.get('JENKINS_SYNC_LOG_ARTIFACTS', False)
        self.sync_xunit_artifacts = self.app.config.get('JENKINS_SYNC_XUNIT_ARTIFACTS', True)
        self.sync_coverage_artifacts = self.app.config.get('JENKINS_SYNC_COVERAGE_ARTIFACTS', True)

    def _get_raw_response(self, path, method='GET', params=None, **kwargs):
        url = '{}/{}'.format(self.base_url, path.lstrip('/'))

        kwargs.setdefault('allow_redirects', False)
        kwargs.setdefault('timeout', 5)
        kwargs.setdefault('auth', self.auth)

        if params is None:
            params = {}

        if self.token is not None:
            params.setdefault('token', self.token)

        self.logger.info('Fetching %r', url)
        resp = getattr(requests, method.lower())(url, params=params, **kwargs)

        if resp.status_code == 404:
            raise NotFound
        elif not (200 <= resp.status_code < 400):
            raise Exception('Invalid response. Status code was %s' % resp.status_code)

        return resp.text

    def _get_json_response(self, path, *args, **kwargs):
        path = '{}/api/json/'.format(path.strip('/'))

        data = self._get_raw_response(path, *args, **kwargs)
        if not data:
            return

        try:
            return json.loads(data)
        except ValueError:
            raise Exception('Invalid JSON data')

    _get_response = _get_json_response

    def _parse_parameters(self, json):
        params = {}
        for action in json['actions']:
            params.update(
                (p['name'], p.get('value'))
                for p in action.get('parameters', [])
            )
        return params

    def _create_job_step(self, phase, job_name=None, build_no=None,
                         label=None, uri=None, **kwargs):
        # TODO(dcramer): we make an assumption that the job step label is unique
        # but its not guaranteed to be the case. We can ignore this assumption
        # by guaranteeing that the JobStep.id value is used for builds instead
        # of the Job.id value.
        defaults = {
            'data': {
                'job_name': job_name,
                'build_no': build_no,
                'uri': uri,
            },
        }
        defaults.update(kwargs)

        data = defaults['data']
        if data['job_name'] and not label:
            label = '{0} #{1}'.format(data['job_name'], data['build_no'] or data['item_id'])

        assert label

        step, created = get_or_create(JobStep, where={
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }, defaults=defaults)

        return step

    def fetch_artifact(self, jobstep, artifact):
        url = '{base}/job/{job}/{build}/artifact/{artifact}'.format(
            base=self.base_url,
            job=jobstep.data['job_name'],
            build=jobstep.data['build_no'],
            artifact=artifact['relativePath'],
        )
        return requests.get(url, stream=True, timeout=15)

    def _sync_artifact_as_xunit(self, jobstep, artifact):
        resp = self.fetch_artifact(jobstep, artifact)

        # TODO(dcramer): requests doesnt seem to provide a non-binary file-like
        # API, so we're stuffing it into StringIO
        try:
            handler = XunitHandler(jobstep)
            handler.process(StringIO(resp.content))
        except Exception:
            db.session.rollback()
            self.logger.exception(
                'Failed to sync test results for job step %s', jobstep.id)
        else:
            db.session.commit()

    def _sync_artifact_as_coverage(self, jobstep, artifact):
        resp = self.fetch_artifact(jobstep, artifact)

        # TODO(dcramer): requests doesnt seem to provide a non-binary file-like
        # API, so we're stuffing it into StringIO
        try:
            handler = CoverageHandler(jobstep)
            handler.process(StringIO(resp.content))
        except Exception:
            db.session.rollback()
            self.logger.exception(
                'Failed to sync test results for job step %s', jobstep.id)
        else:
            db.session.commit()

    def _sync_artifact_as_log(self, jobstep, artifact):
        job = jobstep.job
        logsource, created = get_or_create(LogSource, where={
            'name': artifact['displayPath'],
            'job': job,
            'step': jobstep,
        }, defaults={
            'project': job.project,
            'date_created': job.date_started,
        })

        job_name = jobstep.data['job_name']
        build_no = jobstep.data['build_no']

        url = '{base}/job/{job}/{build}/artifact/{artifact}'.format(
            base=self.base_url, job=job_name,
            build=build_no, artifact=artifact['relativePath'],
        )

        offset = 0
        session = requests.Session()
        with closing(session.get(url, stream=True, timeout=15)) as resp:
            iterator = resp.iter_content()
            for chunk in chunked(iterator, LOG_CHUNK_SIZE):
                chunk_size = len(chunk)
                chunk, _ = create_or_update(LogChunk, where={
                    'source': logsource,
                    'offset': offset,
                }, values={
                    'job': job,
                    'project': job.project,
                    'size': chunk_size,
                    'text': chunk,
                })
                offset += chunk_size

    def _sync_log(self, jobstep, name, job_name, build_no):
        job = jobstep.job
        # TODO(dcramer): this doesnt handle concurrency
        logsource, created = get_or_create(LogSource, where={
            'name': name,
            'job': job,
        }, defaults={
            'step': jobstep,
            'project': jobstep.project,
            'date_created': jobstep.date_started,
        })
        if created:
            offset = 0
        else:
            offset = jobstep.data.get('log_offset', 0)

        url = '{base}/job/{job}/{build}/logText/progressiveText/'.format(
            base=self.base_url,
            job=job_name,
            build=build_no,
        )

        session = requests.Session()
        with closing(session.get(url, params={'start': offset}, stream=True, timeout=15)) as resp:
            log_length = int(resp.headers['X-Text-Size'])

            # When you request an offset that doesnt exist in the build log, Jenkins
            # will instead return the entire log. Jenkins also seems to provide us
            # with X-Text-Size which indicates the total size of the log
            if offset > log_length:
                return

            # XXX: requests doesnt seem to guarantee chunk_size, so we force it
            # with our own helper
            iterator = resp.iter_content()
            for chunk in chunked(iterator, LOG_CHUNK_SIZE):
                chunk_size = len(chunk)
                chunk, _ = create_or_update(LogChunk, where={
                    'source': logsource,
                    'offset': offset,
                }, values={
                    'job': job,
                    'project': job.project,
                    'size': chunk_size,
                    'text': chunk,
                })
                offset += chunk_size

            # Jenkins will suggest to us that there is more data when the job has
            # yet to complete
            has_more = resp.headers.get('X-More-Data') == 'true'

        # We **must** track the log offset externally as Jenkins embeds encoded
        # links and we cant accurately predict the next `start` param.
        jobstep.data['log_offset'] = log_length
        db.session.add(jobstep)

        return True if has_more else None

    def _process_test_report(self, step, test_report):
        test_list = []

        if not test_report:
            return test_list

        for suite_data in test_report['suites']:
            for case in suite_data['cases']:
                message = []
                if case['errorDetails']:
                    message.append('Error\n-----')
                    message.append(case['errorDetails'] + '\n')
                if case['errorStackTrace']:
                    message.append('Stacktrace\n----------')
                    message.append(case['errorStackTrace'] + '\n')
                if case['skippedMessage']:
                    message.append(case['skippedMessage'] + '\n')

                if case['status'] in ('PASSED', 'FIXED'):
                    result = Result.passed
                elif case['status'] in ('FAILED', 'REGRESSION'):
                    result = Result.failed
                elif case['status'] == 'SKIPPED':
                    result = Result.skipped
                else:
                    raise ValueError('Invalid test result: %s' % (case['status'],))

                test_result = TestResult(
                    step=step,
                    name=case['name'],
                    package=case['className'] or None,
                    duration=int(case['duration'] * 1000),
                    message='\n'.join(message).strip(),
                    result=result,
                )
                test_list.append(test_result)
        return test_list

    def _find_job(self, job_name, job_id):
        """
        Given a job identifier, we attempt to poll the various endpoints
        for a limited amount of time, trying to match up either a queued item
        or a running job that has the CHANGES_BID parameter.

        This is nescesary because Jenkins does not give us any identifying
        information when we create a job initially.

        The job_id parameter should be the corresponding value to look for in
        the CHANGES_BID parameter.

        The result is a mapping with the following keys:

        - queued: is it currently present in the queue
        - item_id: the queued item ID, if available
        - build_no: the build number, if available
        """
        # Check the queue first to ensure that we don't miss a transition
        # from queue -> active jobs
        item = self._find_job_in_queue(job_name, job_id)
        if item:
            return item
        return self._find_job_in_active(job_name, job_id)

    def _find_job_in_queue(self, job_name, job_id):
        xpath = QUEUE_ID_XPATH.format(
            job_id=job_id,
        )
        try:
            response = self._get_raw_response('/queue/api/xml/', params={
                'xpath': xpath,
                'wrapper': 'x',
            })
        except NotFound:
            return

        # it's possible that we managed to create multiple jobs in certain
        # situations, so let's just get the newest one
        try:
            match = etree.fromstring(response).iter('id').next()
        except StopIteration:
            return
        item_id = match.text

        # TODO: it's possible this isnt queued when this gets run
        return {
            'job_name': job_name,
            'queued': True,
            'item_id': item_id,
            'build_no': None,
            'uri': None,
        }

    def _find_job_in_active(self, job_name, job_id):
        xpath = BUILD_ID_XPATH.format(
            job_id=job_id,
        )
        try:
            response = self._get_raw_response('/job/{job_name}/api/xml/'.format(
                job_name=job_name,
            ), params={
                'depth': 1,
                'xpath': xpath,
                'wrapper': 'x',
            })
        except NotFound:
            return

        # it's possible that we managed to create multiple jobs in certain
        # situations, so let's just get the newest one
        try:
            match = etree.fromstring(response).iter('number').next()
        except StopIteration:
            return
        build_no = match.text

        return {
            'job_name': job_name,
            'queued': False,
            'item_id': None,
            'build_no': build_no,
            'uri': None,
        }

    def _get_node(self, label):
        node, created = get_or_create(Node, {'label': label})
        if not created:
            return node

        try:
            response = self._get_raw_response('/computer/{}/config.xml'.format(
                label
            ))
        except NotFound:
            return node

        # lxml expects the response to be in bytes, so let's assume it's utf-8
        # and send it back as the original format
        response = response.encode('utf-8')

        xml = objectify.fromstring(response)
        cluster_names = xml.label.text.split(' ')

        for cluster_name in cluster_names:
            # remove swarm client as a cluster label as its not useful
            if cluster_name == 'swarm':
                continue
            cluster, _ = get_or_create(Cluster, {'label': cluster_name})
            get_or_create(ClusterNode, {'node': node, 'cluster': cluster})

        return node

    def _sync_step_from_queue(self, step):
        # TODO(dcramer): when we hit a NotFound in the queue, maybe we should
        # attempt to scrape the list of jobs for a matching CHANGES_BID, as this
        # doesnt explicitly mean that the job doesnt exist
        try:
            item = self._get_response('/queue/item/{}'.format(
                step.data['item_id']))
        except NotFound:
            step.status = Status.finished
            step.result = Result.unknown
            db.session.add(step)
            return

        if item.get('executable'):
            build_no = item['executable']['number']
            step.data['queued'] = False
            step.data['build_no'] = build_no
            step.data['uri'] = item['executable']['url']
            db.session.add(step)

        if item['blocked']:
            step.status = Status.queued
            db.session.add(step)
        elif item.get('cancelled') and not step.data.get('build_no'):
            step.status = Status.finished
            step.result = Result.aborted
            db.session.add(step)
        elif item.get('executable'):
            return self._sync_step_from_active(step)

    def _sync_step_from_active(self, step):
        try:
            job_name = step.data['job_name']
            build_no = step.data['build_no']
        except KeyError:
            raise UnrecoverableException('Missing Jenkins job information')

        try:
            item = self._get_response('/job/{}/{}'.format(
                job_name, build_no))
        except NotFound:
            raise UnrecoverableException('Unable to find job in Jenkins')

        if not step.data.get('uri'):
            step.data['uri'] = item['url']

        # TODO(dcramer): we're doing a lot of work here when we might
        # not need to due to it being sync'd previously
        node = self._get_node(item['builtOn'])

        step.node = node
        step.date_started = datetime.utcfromtimestamp(
            item['timestamp'] / 1000)

        if item['building']:
            step.status = Status.in_progress
        else:
            step.status = Status.finished
            step.result = RESULT_MAP[item['result']]
            step.date_finished = datetime.utcfromtimestamp(
                (item['timestamp'] + item['duration']) / 1000)

        if db.session.is_modified(step):
            db.session.add(step)
            db.session.commit()

        if step.status != Status.finished:
            return

        self._sync_results(step, item)

    def _sync_results(self, step, item):
        job_name = step.data['job_name']
        build_no = step.data['build_no']

        artifacts = item.get('artifacts', ())
        if self.sync_phase_artifacts:
            # if we are allowing phase artifacts and we find *any* artifacts
            # that resemble a phase we need to change the behavior of the
            # the remainder of tasks
            phased_results = any(a['fileName'].endswith('phase.json') for a in artifacts)
        else:
            phased_results = False

        # artifacts sync differently depending on the style of job results
        if phased_results:
            self._sync_phased_results(step, artifacts)
        else:
            self._sync_generic_results(step, artifacts)

        # sync console log
        self.logger.info('Syncing console log for %s', step.id)
        try:
            result = True
            while result:
                result = self._sync_log(
                    jobstep=step,
                    name=step.label,
                    job_name=job_name,
                    build_no=build_no,
                )

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                'Unable to sync console log for job step %r',
                step.id.hex)

    def _handle_generic_artifact(self, jobstep, artifact):
        artifact, created = get_or_create(Artifact, where={
            'step': jobstep,
            'name': artifact['fileName'],
        }, defaults={
            'project': jobstep.project,
            'job': jobstep.job,
            'data': artifact,
        })
        if not created:
            db.session.commit()

        sync_artifact.delay_if_needed(
            artifact_id=artifact.id.hex,
            task_id=artifact.id.hex,
            parent_task_id=jobstep.id.hex,
        )

    def _sync_phased_results(self, step, artifacts):
        # due to the limitations of Jenkins and our requirement to have more
        # insight into the actual steps a build process takes and unfortunately
        # the best way to do this is to rewrite history within Changes
        job = step.job
        project = step.project

        artifacts_by_name = dict(
            (a['fileName'], a)
            for a in artifacts
        )
        pending_artifacts = set(artifacts_by_name.keys())

        phase_steps = set()

        # fetch each phase and create it immediately (as opposed to async)
        for artifact in artifacts:
            artifact_filename = artifact['fileName']

            if not artifact_filename.endswith('phase.json'):
                continue

            pending_artifacts.remove(artifact_filename)

            resp = self.fetch_artifact(step, artifact)
            phase_data = resp.json()

            if phase_data['retcode']:
                result = Result.failed
            else:
                result = Result.passed

            date_started = datetime.utcfromtimestamp(phase_data['startTime'])
            date_finished = datetime.utcfromtimestamp(phase_data['startTime'])

            jobphase, created = get_or_create(JobPhase, where={
                'job': job,
                'label': phase_data['name'],
            }, defaults={
                'project': project,
                'result': result,
                'status': Status.finished,
                'date_started': date_started,
                'date_finished': date_finished,
            })

            jobstep, created = get_or_create(JobStep, where={
                'phase': jobphase,
                'job': job,
            }, defaults={
                'node': step.node,
                'label': jobphase.label,
                'project': project,
                'result': jobphase.result,
                'status': jobphase.status,
                'date_started': jobphase.date_started,
                'date_finished': jobphase.date_finished,
                'data': phase_data,
            })

            phase_steps.add(jobstep)

        for phase_step in phase_steps:
            for artifact in artifacts:
                if artifact['fileName'] == phase_data['log']:
                    log_artifact = artifact
                    break
            else:
                self.logger.warning('Unable to find logfile for phase: %s', phase_data)
                continue

            pending_artifacts.remove(log_artifact['fileName'])

            self._handle_generic_artifact(
                jobstep=phase_step,
                artifact=log_artifact,
            )

        if not pending_artifacts:
            return

        # all remaining artifacts get bound to the final phase
        final_step = sorted(phase_steps, key=lambda x: x.date_finished, reversed=True)[0]
        for artifact_name in pending_artifacts:
            self._handle_generic_artifact(
                jobstep=final_step,
                artifact=artifacts_by_name[artifact_name],
            )

    def _sync_generic_results(self, step, artifacts):
        # sync artifacts
        self.logger.info('Syncing artifacts for %s', step.id)
        for artifact in artifacts:
            self._handle_generic_artifact(jobstep=step, artifact=artifact)

    def sync_job(self, job):
        """
        Steps get created during the create_job and sync_step phases so we only
        rely on those steps syncing.
        """

    def sync_step(self, step):
        if step.data.get('queued'):
            self._sync_step_from_queue(step)
        else:
            self._sync_step_from_active(step)

    def sync_artifact(self, step, artifact):
        if self.sync_log_artifacts and artifact['fileName'].endswith('.log'):
            self._sync_artifact_as_log(step, artifact)
        if self.sync_xunit_artifacts and artifact['fileName'].endswith(XUNIT_FILENAMES):
            self._sync_artifact_as_xunit(step, artifact)
        if self.sync_coverage_artifacts and artifact['fileName'].endswith(COVERAGE_FILENAMES):
            self._sync_artifact_as_coverage(step, artifact)
        db.session.commit()

    def cancel_job(self, job):
        active_steps = JobStep.query.filter(
            JobStep.job == job,
            JobStep.status != Status.finished,
        )
        for step in active_steps:
            try:
                self.cancel_step(step)
            except UnrecoverableException:
                # assume the job no longer exists
                pass

        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

    def cancel_step(self, step):
        if step.data.get('build_no'):
            url = '/job/{}/{}/stop/'.format(
                step.data['job_name'], step.data['build_no'])
        else:
            url = '/queue/cancelItem?id={}'.format(step.data['item_id'])

        try:
            self._get_raw_response(url)
        except NotFound:
            raise UnrecoverableException('Unable to find job in Jenkins')

        step.status = Status.finished
        step.result = Result.aborted
        step.date_finished = datetime.utcnow()
        db.session.add(step)

    def get_job_parameters(self, job, target_id=None):
        if target_id is None:
            target_id = job.id.hex

        params = [
            {'name': 'CHANGES_BID', 'value': target_id},
        ]

        if job.build.source.revision_sha:
            params.append(
                {'name': 'REVISION', 'value': job.build.source.revision_sha},
            )

        if job.build.source.patch:
            params.append(
                {
                    'name': 'PATCH_URL',
                    'value': build_uri('/api/0/patches/{0}/?raw=1'.format(
                        job.build.source.patch.id.hex)),
                }
            )
        return params

    def create_job_from_params(self, target_id, params, job_name=None):
        if job_name is None:
            job_name = self.job_name

        if not job_name:
            raise UnrecoverableException('Missing Jenkins project configuration')

        json_data = {
            'parameter': params
        }

        # TODO: Jenkins will return a 302 if it cannot queue the job which I
        # believe implies that there is already a job with the same parameters
        # queued.
        self._get_response('/job/{}/build'.format(job_name), method='POST', data={
            'json': json.dumps(json_data),
        })

        # we retry for a period of time as Jenkins doesn't have strong consistency
        # guarantees and the job may not show up right away
        t = time.time() + 5
        job_data = None
        while time.time() < t:
            job_data = self._find_job(job_name, target_id)
            if job_data:
                break
            time.sleep(0.3)

        if job_data is None:
            raise Exception('Unable to find matching job after creation. GLHF')

        return job_data

    def get_default_job_phase_label(self, job, job_data):
        return 'Build {0}'.format(job_data['job_name'])

    def create_job(self, job):
        """
        Creates a job within Jenkins.

        Due to the way the API works, this consists of two steps:

        - Submitting the job
        - Polling for the newly created job to associate either a queue ID
          or a finalized build number.
        """
        params = self.get_job_parameters(job)
        job_data = self.create_job_from_params(
            target_id=job.id.hex,
            params=params,
        )

        if job_data['queued']:
            job.status = Status.queued
        else:
            job.status = Status.in_progress
        db.session.add(job)

        phase, created = get_or_create(JobPhase, where={
            'job': job,
            'label': self.get_default_job_phase_label(job, job_data),
            'project': job.project,
        }, defaults={
            'status': job.status,
        })

        if not created:
            return

        # TODO(dcramer): due to no unique constraints this section of code
        # presents a race condition when run concurrently
        step = self._create_job_step(
            phase=phase,
            status=job.status,
            data=job_data,
        )
        db.session.commit()

        sync_job_step.delay(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )
