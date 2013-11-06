from __future__ import absolute_import, division

import json
import logging
import requests

from datetime import datetime
from uuid import uuid4

from changes.backends.base import BaseBackend
from changes.config import db
from changes.constants import Result, Status
from changes.models import RemoteEntity, TestResult


class NotFound(Exception):
    pass


class JenkinsBuilder(BaseBackend):
    provider = 'jenkins'

    def __init__(self, base_url=None, token=None, *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['JENKINS_URL']
        self.token = token or self.app.config['JENKINS_TOKEN']
        self.logger = logging.getLogger('jenkins')

    def _get_response(self, path, method='GET', params=None, **kwargs):
        url = '{}/{}/api/json/'.format(self.base_url, path.strip('/'))

        if params is None:
            params = {}

        params.setdefault('token', self.token)

        self.logger.info('Fetching %r', url)
        resp = getattr(requests, method.lower())(url, params=params, **kwargs)

        if resp.status_code == 404:
            raise NotFound
        elif not (200 <= resp.status_code < 300):
            raise Exception('Invalid response. Status code was %s' % resp.status_code)

        data = resp.text
        if data:
            try:
                return json.loads(data)
            except ValueError:
                raise Exception('Invalid JSON data')
        return

    def _parse_parameters(self, json):
        params = {}
        for action in json['actions']:
            params.update(
                (p['name'], p['value'])
                for p in action.get('parameters', [])
            )
        return params

    def _sync_build_from_queue(self, build, entity):
        # TODO(dcramer); determine whats going on w/ the JSON field
        build_item = entity.data.copy()

        # TODO(dcramer): when we hit a NotFound in the queue, maybe we should
        # attempt to scrape the list of jobs for a matching CHANGES_BID, as this
        # doesnt explicitly mean that the job doesnt exist
        try:
            item = self._get_response('/queue/item/{}'.format(
                build_item['item_id']))
        except NotFound:
            build.status = Status.finished
            build.result = Result.unknown
            db.session.add(build)
            return

        if item.get('executable'):
            build_no = item['executable']['number']
            build_item['queued'] = False
            build_item['build_no'] = build_no
            entity.data = build_item
            db.session.add(entity)

        if item['blocked']:
            build.status = Status.queued
            db.session.add(build)
        elif item.get('cancelled'):
            build.status = Status.finished
            build.result = Result.aborted
            db.session.add(build)
        elif item.get('executable'):
            self._sync_build_from_active(build, entity)

    def _sync_build_from_active(self, build, entity):
        build_item = entity.data.copy()
        try:
            item = self._get_response('/job/{}/{}'.format(
                build_item['job_name'], build_item['build_no']))
        except NotFound:
            build.date_finished = datetime.utcnow()
            build.status = Status.finished
            build.result = Result.aborted
            db.session.add(build)
            return

        should_finish = False

        # XXX(dcramer): timestamp implies creation date, so lets just assume
        # we were able to track it immediately
        if not build.date_started:
            build.date_started = datetime.utcnow()

        if item['building']:
            build.status = Status.in_progress
        else:
            should_finish = True
            build.date_finished = datetime.utcnow()

            if item['result'] == 'SUCCESS':
                build.result = Result.passed
            elif item['result'] == 'ABORTED':
                build.result = Result.aborted
            elif item['result'] in ('FAILURE', 'REGRESSION'):
                build.result = Result.failed
            else:
                raise ValueError('Invalid build result: %s' % (item['result'],))

        if item['duration']:
            build.duration = item['duration']

        build.data = {
            'backend': {
                'uri': item['url'],
                'label': item['fullDisplayName'],
            }
        }

        db.session.add(build)

        for action in item['actions']:
            # is this the best way to find this?
            if action.get('urlName') == 'testReport':
                self._sync_test_results(build, entity)
                break

        if should_finish:
            build.status = Status.finished

    def _sync_test_results(self, build, entity):
        # TODO(dcramer): this doesnt handle concurrency

        build_item = entity.data
        test_report = self._get_response('/job/{}/{}/testReport/'.format(
            build_item['job_name'], build_item['build_no']))

        for suite_data in test_report['suites']:
            suite_name = suite_data.get('name', 'default')

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

                testresult = TestResult(
                    build=build,
                    suite_name=suite_name,
                    name=case['name'],
                    package=case['className'] or None,
                    duration=int(case['duration'] * 1000),
                    message='\n'.join(message).strip(),
                    result=result,
                )
                testresult.save()

    def _find_job(self, job_name, build_id):
        """
        Given a build identifier, we attempt to poll the various endpoints
        for a limited amount of time, trying to match up either a queued item
        or a running job that has the CHANGES_BID parameter.

        This is nescesary because Jenkins does not give us any identifying
        information when we create a job initially.

        The build_id parameter should be the corresponding value to look for in
        the CHANGES_BID parameter.

        The result is a mapping with the following keys:

        - queued: is it currently present in the queue
        - item_id: the queued item ID, if available
        - build_no: the build number, if available
        """
        # Check the queue first to ensure that we don't miss a transition
        # from queue -> active builds
        for item in self._get_response('/queue')['items']:
            if item['task']['name'] != job_name:
                continue

            params = self._parse_parameters(item)
            try:
                job_build_id = params['CHANGES_BID']
            except KeyError:
                continue

            if job_build_id == build_id:
                return {
                    'job_name': job_name,
                    'queued': True,
                    'item_id': item['id'],
                    'build_no': None,
                }

        # It wasn't found in the queue, so lets look for an active build
        # the depth=2 is important here, otherwise parameters are not included
        for item in self._get_response('/job/{}'.format(job_name), params={'depth': 2})['builds']:
            params = self._parse_parameters(item)
            try:
                job_build_id = params['CHANGES_BID']
            except KeyError:
                continue

            if job_build_id == build_id:
                return {
                    'job_name': job_name,
                    'queued': False,
                    'item_id': None,
                    'build_no': item['number'],
                }

    def sync_build(self, build):
        entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=build.id,
            type='build',
        ).first()
        if not entity:
            return

        if entity.data['queued']:
            self._sync_build_from_queue(build, entity)
        else:
            self._sync_build_from_active(build, entity)

    def create_build(self, build):
        """
        Creates a build within Jenkins.

        Due to the way the API works, this consists of two steps:

        - Submitting the build
        - Polling for the newly created build to associate either a queue ID
          or a finalized build number.
        """

        # TODO: patch support
        entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=build.project.id,
            type='job',
        ).first()
        if not entity:
            raise Exception('Missing Jenkins project configuration')
        job_name = entity.remote_id

        json_data = {
            'parameter': [
                {'name': 'REVISION', 'value': build.parent_revision_sha},
                {'name': 'CHANGES_BID', 'value': build.id.hex},
            ]
        }
        # TODO: Jenkins will return a 302 if it cannot queue the job which I
        # believe implies that there is already a job with the same parameters
        # queued.
        self._get_response('/job/{}/build'.format(job_name), method='POST', data={
            'json': json.dumps(json_data),
        })

        build_item = self._find_job(job_name, build.id.hex)
        if build_item is None:
            raise Exception('Unable to find matching job after creation. GLHF')

        # we generate a random remote_id as the queue's item_ids seem to reset
        # when jenkins restarts, which would create duplicates
        remote_id = uuid4().hex

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            type='build',
            remote_id=remote_id,
            data=build_item,
        )
        db.session.add(entity)
