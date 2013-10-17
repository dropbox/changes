from __future__ import absolute_import, division

import json
import requests
import sys

from collections import defaultdict
from datetime import datetime, timedelta

from changes.backends.base import BaseBackend
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import create_or_update
from changes.models import (
    Revision, Author, Phase, Step, RemoteEntity, Node
)


class KoalityBuilder(BaseBackend):
    provider = 'koality'

    def __init__(self, base_url=None, api_key=None, *args, **kwargs):
        super(KoalityBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['KOALITY_URL']
        self.api_key = api_key or self.app.config['KOALITY_API_KEY']
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

        try:
            node = RemoteEntity.query.filter_by(
                type='node',
                remote_id=str(node_id),
                provider=self.provider,
            )[0]
        except IndexError:
            node = Node()
            entity = RemoteEntity(
                provider=self.provider, remote_id=str(node_id),
                internal_id=node.id, type='node',
            )
            db.session.add(node)
            db.session.add(entity)

        self._node_cache[node_id] = node

        return node

    def _sync_author(self, user):
        author = create_or_update(Author, values={
            'email': user['email'],
        }, where={
            'name': user['name'],
        })
        db.session.add(author)
        return author

    def _sync_revision(self, repository, author, commit):
        revision = create_or_update(Revision, values={
            'message': commit['message'],
            'author': author,
        }, where={
            'repository': repository,
            'sha': commit['sha'],
        })
        db.session.add(revision)
        return revision

    def _sync_phase(self, build, stage_type, stage_list, phase=None):
        remote_id = '%s:%s' % (build.id.hex, stage_type)

        if phase is None:
            try:
                entity = RemoteEntity.query.filter_by(
                    type='phase',
                    provider=self.provider,
                    remote_id=remote_id,
                )[0]
            except IndexError:
                phase, entity = None, None
            else:
                phase = Phase.query.get(entity.internal_id)
            create_entity = entity is None
        else:
            create_entity = False

        if phase is None:
            phase = Phase()

        phase.build = build
        phase.repository = build.repository
        phase.project = build.project
        phase.label = stage_type.title()

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

        if create_entity:
            entity = RemoteEntity(
                provider=self.provider, remote_id=remote_id,
                internal_id=phase.id, type='phase',
            )
            db.session.add(entity)

        db.session.add(phase)

        return phase

    def _sync_step(self, build, phase, stage, step=None):
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
                step = Step.query.get(entity.internal_id)
            create_entity = entity is None
        else:
            create_entity = False

        if step is None:
            step = Step()

        node = self._get_node(stage['buildNode'])

        step.build = build
        step.repository = build.repository
        step.project = build.project
        step.phase = phase
        step.node = node
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

    def _sync_build_details(self, build, change, stage_list=None):
        project = build.project

        author = self._sync_author(change['headCommit']['user'])
        parent_revision = self._sync_revision(
            project.repository, author, change['headCommit'])

        build.label = change['headCommit']['message'].splitlines()[0][:128]
        build.author = author
        build.parent_revision_sha = parent_revision.sha
        build.repository = project.repository
        build.project = project

        if stage_list is not None:
            build.date_created = datetime.utcfromtimestamp(change['createTime'] / 1000)
            build.date_started = self._get_start_time(stage_list)
            build.date_finished = self._get_end_time(stage_list)

            if change['startTime']:
                build.date_started = min(
                    build.date_started,
                    datetime.utcfromtimestamp(change['startTime'] / 1000))

            # for stage in (s for s in stages if s['status'] == 'failed'):
            if build.date_started and build.date_finished:
                if all(s['status'] == 'passed' for s in stage_list):
                    build.result = Result.passed
                else:
                    build.result = Result.failed
                build.status = Status.finished
            elif build.date_started:
                if any(s['status'] == 'failed' for s in stage_list):
                    build.result = Result.failed
                else:
                    build.result = Result.unknown
                build.status = Status.in_progress
            else:
                build.status = Status.queued
                build.result = Result.unknown
        elif change['startTime'] and not build.date_started:
            build.date_started = datetime.utcfromtimestamp(
                change['startTime'] / 1000)

            if build.status in (Status.queued, Status.unknown):
                build.status = Status.in_progress
        elif build.status == Status.unknown:
                build.status = Status.queued

        # 'timeout' jobs that dont seem to be doing anything
        now = datetime.utcnow()
        check_time = datetime.utcfromtimestamp(max(change['startTime'], change['createTime']) / 1000.0)
        cutoff = timedelta(minutes=90)
        if build.status in (Status.queued, Status.in_progress, Status.unknown) and check_time < now - cutoff:
            build.status = Status.finished
            build.result = Result.timedout

        db.session.add(build)

    def sync_build_details(self, build):
        project = build.project
        project_entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=project.id,
            type='project',
        )[0]
        build_entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=build.id,
            type='build',
        )[0]

        remote_id = build_entity.remote_id
        project_id = project_entity.remote_id

        # {u'branch': u'verify only (api)', u'number': 760, u'createTime': 1379712159000, u'headCommit': {u'sha': u'257e20ba86c5fe1ff1e1f44613a2590bb56d7285', u'message': u'Change format of mobile gandalf info\n\nSummary: Made it more prettier\n\nTest Plan: tried it with my emulator, it works\n\nReviewers: fta\n\nReviewed By: fta\n\nCC: Reviews-Aloha, Server-Reviews\n\nDifferential Revision: https://tails.corp.dropbox.com/D23207'}, u'user': {u'lastName': u'Verifier', u'id': 3, u'firstName': u'Koality', u'email': u'verify-koala@koalitycode.com'}, u'startTime': 1379712161000, u'mergeStatus': None, u'endTime': 1379712870000, u'id': 814}
        change = self._get_response('GET', '{base_uri}/api/v/0/repositories/{project_id}/changes/{build_id}'.format(
            base_uri=self.base_url, project_id=project_id, build_id=remote_id
        ))

        # [{u'status': u'passed', u'type': u'compile', u'id': 18421, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18427, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18426, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18408, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18409, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18428, u'name': u'blockserver'}, {u'status': u'passed', u'type': u'test', u'id': 18429, u'name': u'dropbox'}, {u'status': u'passed', u'type': u'compile', u'id': 18422, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18431, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18430, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18406, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18412, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18432, u'name': u'magicpocket'}, {u'status': u'passed', u'type': u'compile', u'id': 18433, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18441, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18437, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18407, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18411, u'name': u'provision'}, {u'status': u'passed', u'type': u'compile', u'id': 18420, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18424, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18423, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18405, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18410, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18425, u'name': u'metaserver'}]
        stage_list = self._get_response('GET', '{base_uri}/api/v/0/repositories/{project_id}/changes/{build_id}/stages'.format(
            base_uri=self.base_url, project_id=project_id, build_id=remote_id
        ))

        self._sync_build_details(build, change, stage_list)

        grouped_stages = defaultdict(list)
        for stage in stage_list:
            grouped_stages[stage['type']].append(stage)

        for stage_type, stage_list in grouped_stages.iteritems():
            stage_list.sort(key=lambda x: x['status'] == 'passed')

            phase = self._sync_phase(build, stage_type, stage_list)

            for stage in stage_list:
                self._sync_step(build, phase, stage)

        return build

    def create_build(self, build):
        project = build.project
        project_entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=project.id,
            type='project',
        )[0]

        req_kwargs = {}
        if build.patch:
            req_kwargs['files'] = {
                'patch': build.patch.diff,
            }

        response = self._get_response('POST', '{base_uri}/api/v/0/repositories/{project_id}/changes'.format(
            base_uri=self.base_url, project_id=project_entity.remote_id,
        ), data={
            'sha': build.parent_revision_sha,
        }, **req_kwargs)

        entity = RemoteEntity(
            provider=self.provider, remote_id=str(response['changeId']),
            internal_id=build.id, type='build',
        )
        db.session.add(entity)

        return entity
