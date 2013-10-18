from __future__ import absolute_import, division

import json
import logging
import requests

from datetime import datetime

from changes.backends.base import BaseBackend
from changes.config import db
from changes.constants import Result, Status
from changes.models import RemoteEntity


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

        if not (200 <= resp.status_code < 300):
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
        build_item = entity.data

        item = self._get_response('/queue/item/{}'.format(
            build_item['item_id']))

        if item['blocked']:
            build.status = Status.queued
            db.session.add(build)
        elif item['cancelled']:
            build.status = Status.finished
            build.result = Result.aborted
            db.session.add(build)
        else:
            build_no = item['executable']['number']
            build_item['build_no'] = build_no
            db.session.add(entity)
            self._sync_build_from_active(build, entity)

    def _sync_build_from_active(self, build, entity):
        build_item = entity.data
        item = self._get_response('/job/{}/{}'.format(
            build_item['job_name'], build_item['build_no']))

        if item['timestamp'] and not build.date_started:
            build.date_started = datetime.utcfromtimestamp(
                item['timestamp'] / 1000)

        if item['building']:
            build.status = Status.in_progress
        else:
            build.date_finished = datetime.utcnow()

        if item['result']:
            build.status = Status.finished
            if item['result'] == 'SUCCESS':
                build.result = Result.passed
            elif item['result'] == 'ABORTED':
                build.result = Result.aborted
            elif item['result'] == 'FAILED':
                build.result = Result.failed

        if item['duration']:
            build.duration = item['duration'] * 1000

        db.session.add(build)

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
        )[0]

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
        )[0]
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

        if build_item['queued']:
            remote_id = 'queue:{}'.format(build_item['item_id'])
        else:
            remote_id = '{}#{}'.format(build_item['job_name'], build_item['build_no'])

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            type='build',
            remote_id=remote_id,
            data=build_item,
        )
        db.session.add(entity)
