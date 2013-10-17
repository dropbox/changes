from __future__ import absolute_import, division

import json
import logging
import requests

from sqlalchemy import and_

from changes.backends.base import BaseBackend
from changes.config import db
from changes.constants import Result, Status
from changes.jobs.sync_build import sync_build
from changes.models import (
    Revision, Author, Phase, Step, RemoteEntity, EntityType, Node,
    Build, Project
)


class JenkinsBuilder(BaseBackend):
    def __init__(self, base_url=None, *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['JENKINS_URL']
        self.logger = logging.getLogger('jenkins')

    def _get_response(self, path):
        url = '{}/{}/api/json'.format(self.base_url, path.strip('/'))

        self.logger.info('Fetching %r', url)
        resp = requests.get(url, verify=False)

        if resp.status_code != 200:
            return None

        try:
            return resp.json()
        except json.JSONDecodeError:
            return None

    def _parse_parameters(self, json):
        params = {}
        for action in json['actions']:
            params.update(
                (p['name'], p['value'])
                for p in action.get('parameters', [])
            )
        return params

    def sync_build_list(self, project):
        """
        We synchronize builds by first traversing jobs in the queue, and then
        (serially, this is important!) traversing builds.

        If a job is not in the queue, and then not listed in the builds, we
        assume it was aborted or some other system failure happened.

        If a job is not finalized (that is, Build.status is not finished) then
        we assume that a synchronization is required for said job.
        """
        entity = project.get_entity('jenkins')
        job_name = entity.remote_id
        last_build_no = entity.data.get('last_build_no')
        # XXX: it's possible to actually have truncated build results here so
        # that build ID of 0 doesnt exist, so we need to find the minimum ID
        if last_build_no is None:
            response = self._get_response('/job/{}'.format(job_name))
            last_build_no = min(
                b['number']
                for b in response['builds']
            )
            max_build_no = response['nextBuildNumber'] - 1
        else:
            max_build_no = None

        queued_build_ids = set()
        for item in self._get_response('/queue')['items']:
            params = self._parse_parameters(item)
            try:
                queued_build_ids.add(params['CHANGES_BID'])
            except KeyError:
                continue

        # TODO(dcramer): ideally this happens via the queue so it can scale
        # on the workers automatically. At the very least, we can use a
        # threadpool to do all of these async and join on the results
        build_id_map = {}
        build_no = last_build_no
        while True:
            # TODO: handle that 404 that we're bound to hit if max_build_no
            # is not defined
            item = self._get_response('/job/{}/{}'.format(job_name, build_no))

            params = self._parse_parameters(item)
            try:
                build_id_map[params['CHANGES_BID']] = item
            except KeyError:
                pass

            if build_no == max_build_no:
                break

            build_no += 1

        # pull out the builds that we queried against
        matched_builds = Build.query.filter(
            and_(Build.id.in_(build_id_map.keys()), Build.status != Status.finished)
        )

        # update last_build_no to be the minimum build_no that is unfinished
        # XXX(dcramer): this also has to happen as part of updating individual
        # builds, but this gives us a safetey net
        if not matched_builds:
            return

        last_build_no = max(last_build_no, min(
            build_id_map[b.id.hex]['number']
            for b in matched_builds
        ))

        # Fire off an update to ensure it exists in the queue
        # (the update may not actually happen due to timing/locking measures)
        for build in matched_builds:
            sync_build.delay(build_id=build.id)

        entity.data['last_build_no'] = last_build_no
        db.session.add(entity)

    def create_build(self, build):
        entity = build.project.get_entity('jenkins')
        job_name = entity.remote_id

        url = '%s/job/%s/build' % (self.base_url, job_name)
        json_data = {
            'parameter': [
                {'name': 'CHANGES_BID', 'value': build.id.hex},
            ]
        }
        resp = requests.post(url, data={
            'json': json.dumps(json_data),
        })
        assert resp.status_code == 201
