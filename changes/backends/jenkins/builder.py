from __future__ import absolute_import, division

import json
import logging
import requests
import time

from datetime import datetime
from hashlib import sha1
from flask import current_app
from uuid import uuid4

from changes.backends.base import BaseBackend
from changes.config import db, queue
from changes.constants import Result, Status
from changes.db.utils import create_or_update, get_or_create
from changes.models import (
    AggregateTestSuite, RemoteEntity, TestResult, TestResultManager, TestSuite,
    LogSource, LogChunk
)

LOG_CHUNK_SIZE = 4096


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

    def __init__(self, base_url=None, token=None, *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['JENKINS_URL']
        self.token = token or self.app.config['JENKINS_TOKEN']
        self.sync_artifacts = self.app.config['JENKINS_SYNC_ARTIFACTS']
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
                (p['name'], p.get('value'))
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
        elif item.get('cancelled') and not build_item.get('build_no'):
            build.status = Status.finished
            build.result = Result.aborted
            db.session.add(build)
        elif item.get('executable'):
            for x in xrange(6):
                # There's a possible race condition where the item has been
                # assigned an ID, yet the API responds as if the build does
                # not exist
                try:
                    self._sync_build_from_active(build, entity, fail_on_404=True)
                except NotFound:
                    time.sleep(0.3)
                else:
                    break

    def _sync_build_from_active(self, build, entity, fail_on_404=False):
        build_item = entity.data.copy()
        try:
            item = self._get_response('/job/{}/{}'.format(
                build_item['job_name'], build_item['build_no']))
        except NotFound:
            if fail_on_404:
                raise
            build.date_finished = datetime.utcnow()
            build.status = Status.finished
            build.result = Result.unknown
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
        db.session.commit()

        # TODO(dcramer): ideally we could fire off jobs to sync test results
        # and console logs
        for action in item['actions']:
            # is this the best way to find this?
            if action.get('urlName') == 'testReport':
                try:
                    self._sync_test_results(build, entity)
                except Exception:
                    db.session.rollback()
                    current_app.logger.exception('Unable to sync test results for build %r', build.id.hex)

        if should_finish:
            # FIXME(dcramer): we're waiting until the build is complete to sync
            # logs due to our inability to correctly identify start offsets
            # if we're supposed to be finishing, lets ensure we actually
            # get the entirety of the log
            try:
                start = time.time()
                while self._sync_console_log(build, entity):
                    if time.time() - start > 15:
                        raise Exception('Took too long to sync log')
                    continue
            except Exception:
                db.session.rollback()
                current_app.logger.exception('Unable to sync console log for build %r', build.id.hex)

            if self.sync_artifacts:
                for artifact in item.get('artifacts', ()):
                    queue.delay('sync_artifact', kwargs={
                        'build_id': build.id.hex,
                        'artifact': artifact,
                    })

            build.status = Status.finished
            db.session.add(build)

    def _sync_artifact_as_log(self, build, entity, artifact):
        build_item = entity.data

        logsource, created = get_or_create(LogSource, where={
            'name': artifact['displayPath'],
            'build': build,
        }, defaults={
            'project': build.project,
            'date_created': build.date_started,
        })

        url = '{base}/job/{job}/{build}/artifact/{artifact}'.format(
            base=self.base_url, job=build_item['job_name'],
            build=build_item['build_no'], artifact=artifact['relativePath'],
        )

        offset = 0
        resp = requests.get(url, stream=True)
        iterator = resp.iter_content()
        for chunk in chunked(iterator, LOG_CHUNK_SIZE):
            chunk_size = len(chunk)
            create_or_update(LogChunk, where={
                'source': logsource,
                'offset': offset,
            }, values={
                'build': build,
                'project': build.project,
                'size': chunk_size,
                'text': chunk,
            })
            offset += chunk_size
            db.session.commit()

    def _sync_console_log(self, build, entity):
        # TODO(dcramer): this doesnt handle concurrency
        build_item = entity.data
        logsource, created = get_or_create(LogSource, where={
            'name': 'console',
            'build': build,
        }, defaults={
            'project': build.project,
            'date_created': build.date_started,
        })
        if created:
            offset = 0
        else:
            offset = build_item.get('log_offset', 0)

        url = '{base}/job/{job}/{build}/logText/progressiveHtml/'.format(
            base=self.base_url, job=build_item['job_name'],
            build=build_item['build_no'],
        )

        resp = requests.get(url, params={'start': offset}, stream=True)
        log_length = int(resp.headers['X-Text-Size'])
        # When you request an offset that doesnt exist in the build log, Jenkins
        # will instead return the entire log. Jenkins also seems to provide us
        # with X-Text-Size which indicates the total size of the log
        if offset > log_length:
            return

        iterator = resp.iter_content()
        # XXX: requests doesnt seem to guarantee chunk_size, so we force it
        # with our own helper
        for chunk in chunked(iterator, LOG_CHUNK_SIZE):
            chunk_size = len(chunk)
            create_or_update(LogChunk, where={
                'source': logsource,
                'offset': offset,
            }, values={
                'build': build,
                'project': build.project,
                'size': chunk_size,
                'text': chunk,
            })
            db.session.commit()
            offset += chunk_size

        # We **must** track the log offset externally as Jenkins embeds encoded
        # links and we cant accurately predict the next `start` param.
        build_item['log_offset'] = log_length
        entity.data = build_item
        db.session.add(entity)
        db.session.commit()

        # Jenkins will suggest to us that there is more data when the job has
        # yet to complete
        return True if resp.headers.get('X-More-Data') == 'true' else None

    def _sync_test_results(self, build, entity):
        build_item = entity.data
        test_report = self._get_response('/job/{}/{}/testReport/'.format(
            build_item['job_name'], build_item['build_no']))

        test_list = []
        for suite_data in test_report['suites']:
            suite_name = suite_data.get('name', 'default')

            # TODO(dcramer): this is not specific to Jenkins and should be
            # abstracted
            suite, _ = get_or_create(TestSuite, where={
                'build': build,
                'name_sha': sha1(suite_name).hexdigest(),
            }, defaults={
                'name': suite_name,
                'project': build.project,
            })

            agg, created = get_or_create(AggregateTestSuite, where={
                'project': build.project,
                'name_sha': suite.name_sha,
            }, defaults={
                'name': suite.name,
                'first_build_id': build.id,
            })

            if not created:
                db.session.query(AggregateTestSuite).filter(
                    AggregateTestSuite.id == agg.id,
                ).update({
                    AggregateTestSuite.last_build_id: build.id,
                }, synchronize_session=False)

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
                    build=build,
                    suite=suite,
                    name=case['name'],
                    package=case['className'] or None,
                    duration=int(case['duration'] * 1000),
                    message='\n'.join(message).strip(),
                    result=result,
                )
                test_list.append(test_result)

        manager = TestResultManager(build)
        manager.save(test_list)
        db.session.commit()

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

    def sync_artifact(self, build, artifact):
        entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=build.id,
            type='build',
        ).first()
        if not entity:
            return

        if artifact['fileName'].endswith('.log'):
            self._sync_artifact_as_log(build, entity, artifact)

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
                {'name': 'CHANGES_BID', 'value': build.id.hex},
            ]
        }
        if build.revision_sha:
            json_data['parameter'].append(
                {'name': 'REVISION', 'value': build.revision_sha},
            )

        if build.patch:
            json_data['parameter'].append(
                {'name': 'PATCH', 'file': 'patch'}
            )
            files = {
                'patch': build.patch.diff,
            }
        else:
            files = None

        # TODO: Jenkins will return a 302 if it cannot queue the job which I
        # believe implies that there is already a job with the same parameters
        # queued.
        self._get_response('/job/{}/build'.format(job_name), method='POST', data={
            'json': json.dumps(json_data),
        }, files=files)

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
        return entity
