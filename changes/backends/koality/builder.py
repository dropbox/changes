from __future__ import absolute_import, division

import json
import requests
import sys

from collections import defaultdict
from datetime import datetime, timedelta

from changes.backends.base import BaseBackend, UnrecoverableException
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.models import JobPhase, JobStep, RemoteEntity, Node


class KoalityBuilder(BaseBackend):
    provider = 'koality'

    def __init__(self, base_url=None, api_key=None, project_id=None,
                 *args, **kwargs):
        super(KoalityBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['KOALITY_URL']
        self.api_key = api_key or self.app.config['KOALITY_API_KEY']
        self.project_id = project_id
        self._node_cache = {}

    def _get_end_time(self, stage_list):
        end_time = 0
        for stage in stage_list:
            if not stage.get('endTime'):
                return
            end_time = max((stage['endTime'], end_time))

        if end_time != 0:
            return datetime.utcfromtimestamp(end_time / 1000)
        return

    def _get_start_time(self, stage_list):
        start_time = sys.maxint
        for stage in stage_list:
            if not stage.get('startTime'):
                continue
            start_time = min((stage['startTime'], start_time))

        if start_time not in (0, sys.maxint):
            return datetime.utcfromtimestamp(start_time / 1000)
        return

        datetime.utcfromtimestamp(
            min(s['startTime'] for s in stage_list if s['startTime']) / 1000,
        )

    def _get_response(self, method, url, **kwargs):
        kwargs.setdefault('params', {})
        # TODO(dcramer): ensure SSL is usable
        kwargs.setdefault('verify', False)
        kwargs['params'].setdefault('key', self.api_key)
        response = getattr(requests, method.lower())(url, **kwargs)
        data = response.text
        try:
            return json.loads(data)
        except ValueError:
            raise Exception(data)

    def _get_node(self, node_id):
        node = self._node_cache.get(node_id)
        if node is not None:
            return node

        entity = RemoteEntity.query.filter_by(
            type='node',
            remote_id=str(node_id),
            provider=self.provider,
        ).first()
        if entity is None:
            node = Node()
            entity = RemoteEntity(
                provider=self.provider, remote_id=str(node_id),
                internal_id=node.id, type='node',
            )
            db.session.add(node)
            db.session.add(entity)
        else:
            node = Node.query.get(entity.internal_id)
            assert node

        self._node_cache[node_id] = node

        return node

    def _sync_phase(self, job, stage_type, stage_list):
        phase, _ = get_or_create(
            JobPhase,
            where={
                'job_id': job.id,
                'label': stage_type.title(),
            },
            defaults={
                'repository_id': job.repository_id,
                'project_id': job.project_id,
            },
        )

        phase.date_started = self._get_start_time(stage_list)
        phase.date_finished = self._get_end_time(stage_list)

        # for stage in (s for s in stages if s['status'] == 'failed'):
        if phase.date_started and phase.date_finished:
            if all(s['status'] == 'passed' for s in stage_list):
                phase.result = Result.passed
            else:
                phase.result = Result.failed
            phase.status = Status.finished
        elif phase.date_started:
            if any(s['status'] == 'failed' for s in stage_list):
                phase.result = Result.failed
            else:
                phase.result = Result.unknown
            phase.status = Status.in_progress
        else:
            phase.status = Status.queued
            phase.result = Result.unknown

        db.session.add(phase)
        db.session.commit()

        return phase

    def _sync_step(self, job, phase, stage, step=None):
        if step is None:
            try:
                entity = RemoteEntity.query.filter_by(
                    type='step',
                    provider=self.provider,
                    remote_id=str(stage['id']),
                )[0]
            except IndexError:
                step, entity = None, None
            else:
                step = JobStep.query.get(entity.internal_id)
            create_entity = entity is None
        else:
            create_entity = False

        if step is None:
            step = JobStep()

        node = self._get_node(stage['buildNode'])

        step.job_id = job.id
        step.repository_id = job.repository_id
        step.project_id = job.project_id
        step.phase_id = phase.id
        step.node_id = node.id
        step.label = stage['name']
        step.date_started = self._get_start_time([stage])
        step.date_finished = self._get_end_time([stage])

        if step.date_started and step.date_finished:
            if stage['status'] == 'passed':
                step.result = Result.passed
            else:
                step.result = Result.failed
            step.status = Status.finished
        elif step.date_started:
            if stage['status'] == 'failed':
                step.result = Result.failed
            else:
                step.result = Result.unknown
            step.status = Status.in_progress
        else:
            step.status = Status.queued
            step.result = Result.unknown

        if create_entity:
            entity = RemoteEntity(
                provider=self.provider, remote_id=str(stage['id']),
                internal_id=step.id, type='step',
            )
            db.session.add(entity)

        db.session.add(step)

        return step

    def _sync_job_details(self, job, change, stage_list=None):
        if stage_list is not None:
            job.date_started = self._get_start_time(stage_list)
            job.date_finished = self._get_end_time(stage_list)

            if change['startTime']:
                if job.date_started:
                    job.date_started = min(
                        job.date_started,
                        datetime.utcfromtimestamp(change['startTime'] / 1000))
                else:
                    job.date_started = datetime.utcfromtimestamp(change['startTime'] / 1000)

            # for stage in (s for s in stages if s['status'] == 'failed'):
            if job.date_started and job.date_finished:
                if all(s['status'] == 'passed' for s in stage_list):
                    job.result = Result.passed
                else:
                    job.result = Result.failed
                job.status = Status.finished
            elif job.date_started:
                if any(s['status'] == 'failed' for s in stage_list):
                    job.result = Result.failed
                else:
                    job.result = Result.unknown
                job.status = Status.in_progress
            else:
                job.status = Status.queued
                job.result = Result.unknown
        elif change['startTime'] and not job.date_started:
            job.date_started = datetime.utcfromtimestamp(
                change['startTime'] / 1000)

            if job.status in (Status.queued, Status.unknown):
                job.status = Status.in_progress
        elif job.status == Status.unknown:
                job.status = Status.queued

        # 'timeout' jobs that dont seem to be doing anything
        now = datetime.utcnow()
        check_time = datetime.utcfromtimestamp(max(change['startTime'], change['createTime']) / 1000.0)
        cutoff = timedelta(minutes=90)
        if job.status in (Status.queued, Status.in_progress, Status.unknown) and check_time < now - cutoff:
            job.status = Status.finished
            job.result = Result.failed

        db.session.add(job)

    def sync_job(self, job):
        # {u'branch': u'verify only (api)', u'number': 760, u'createTime': 1379712159000, u'headCommit': {u'sha': u'257e20ba86c5fe1ff1e1f44613a2590bb56d7285', u'message': u'Change format of mobile gandalf info\n\nSummary: Made it more prettier\n\nTest Plan: tried it with my emulator, it works\n\nReviewers: fta\n\nReviewed By: fta\n\nCC: Reviews-Aloha, Server-Reviews\n\nDifferential Revision: https://tails.corp.dropbox.com/D23207'}, u'user': {u'lastName': u'Verifier', u'id': 3, u'firstName': u'Koality', u'email': u'verify-koala@koalitycode.com'}, u'startTime': 1379712161000, u'mergeStatus': None, u'endTime': 1379712870000, u'id': 814}
        change = self._get_response('GET', '{base_uri}/api/v/0/repositories/{project_id}/changes/{change_id}'.format(
            base_uri=self.base_url,
            project_id=job.data['project_id'],
            change_id=job.data['change_id'],
        ))

        # [{u'status': u'passed', u'type': u'compile', u'id': 18421, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18427, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18426, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18408, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18409, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18428, u'name': u'blockserver'}, {u'status': u'passed', u'type': u'test', u'id': 18429, u'name': u'dropbox'}, {u'status': u'passed', u'type': u'compile', u'id': 18422, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18431, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18430, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18406, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18412, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18432, u'name': u'magicpocket'}, {u'status': u'passed', u'type': u'compile', u'id': 18433, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18441, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18437, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18407, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18411, u'name': u'provision'}, {u'status': u'passed', u'type': u'compile', u'id': 18420, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18424, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18423, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18405, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18410, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18425, u'name': u'metaserver'}]
        stage_list = self._get_response('GET', '{base_uri}/api/v/0/repositories/{project_id}/changes/{change_id}/stages'.format(
            base_uri=self.base_url,
            project_id=job.data['project_id'],
            change_id=job.data['change_id'],
        ))

        self._sync_job_details(job, change, stage_list)

        grouped_stages = defaultdict(list)
        for stage in stage_list:
            grouped_stages[stage['type']].append(stage)

        for stage_type, stage_list in grouped_stages.iteritems():
            stage_list.sort(key=lambda x: x['status'] == 'passed')

            phase = self._sync_phase(job, stage_type, stage_list)

            for stage in stage_list:
                self._sync_step(job, phase, stage)

        return job

    def create_job(self, job):
        project_id = self.project_id
        if not project_id:
            raise UnrecoverableException('Missing Koality project configuration')

        req_kwargs = {}
        if job.patch:
            req_kwargs['files'] = {
                'patch': job.patch.diff,
            }

        response = self._get_response('POST', '{base_uri}/api/v/0/repositories/{project_id}/changes'.format(
            base_uri=self.base_url, project_id=project_id,
        ), data={
            # XXX: passing an empty value for email causes Koality to not
            # send out an email notification
            'emailTo': '',
            'sha': job.revision_sha,
        }, **req_kwargs)

        job.data = {
            'project_id': project_id,
            'change_id': response['changeId'],
        }
        db.session.add(job)
