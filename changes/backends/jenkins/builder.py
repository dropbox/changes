from __future__ import absolute_import, division

import json
import requests
import sys

from cStringIO import StringIO
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from changes.backends.base import BaseBackend
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import create_or_update
from changes.jobs.sync_build import sync_build
from changes.models import (
    Revision, Author, Phase, Step, RemoteEntity, EntityType, Node,
    Build, Project
)



# def sync_artifacts():
#     url = '{}/job/server-run-task/api/json'.format(app.config['JENKINS_URL'])
#     resp = requests.get(url)
#     if resp.status_code != 200:
#         return

#     data = resp.json()
#     job_name = data['name']
#     for build in data['builds']:
#         logging.info("Creating process_artifacts job for %s#%s", job_name, build['number'])
#         process_artifacts.delay(
#             job_name=job_name,
#             build_number=build['number'],
#         )

# def sync_build(build_id):
#     """ Syncs the data for a build in the db with the data in Jenkins.
#     """
#     assert build_no

#     job_name = Jenkins.JENKINS_JOB
#     jenkins_data = Jenkins.get_build(build_no)
#     if not jenkins_data:
#         # build isn't found on Jenkins yet (or anymore...)
#         return

#     # For some reason the build status is SUCCESS while the build is still running.
#     if jenkins_data.get('inQueue'):
#         build_status = BuildStatus.QUEUED
#     elif jenkins_data.get('building') or jenkins_data.get('running') or jenkins_data.get('result') is None:
#         build_status = BuildStatus.RUNNING
#     else:
#         build_status = Build._parse_build_status(jenkins_data['result'])

#     parameters = parse_parameters(jenkins_data)
#     project_id = parameters.get('BUILDBOX_PROJECT_ID')
#     build_id_hex = parameters.get('BUILDBOX_BUILD_ID')
#     build_id = UUID(hex=build_id_hex) if build_id_hex else None
#     build_no = jenkins_data['number']

#     if not build_id:
#         logging.error('%s#%s missing BUIDLBOX_BUILD_ID', job_name, build_no)
#         return
#     if not project_id:
#         logging.error('%s#%s missing BUILDBOX_PROJECT_ID', job_name, build_no)
#         return

#     # TODO(pw): this is racy, need to add locking...
#     build = Build.query.get(build_id.bytes)
#     if not build:
#         logging.error('Build %s does not exist', build_id_hex)
#         return
#         # timestamp = jenkins_data.get('timestamp')
#         # created_date = (
#         #         datetime.datetime.fromtimestamp(timestamp / 1000, tz=pytz.utc)
#         #         if timestamp else None)
#         # build = Build.add(
#         #     project_id=project_id,
#         #     patch_url=parameters.get('BUILDBOX_PATCH_URL'),
#         #     revision=parameters.get('BUILDBOX_REVISION'),
#         #     build_id=build_id,
#         #     build_no=build_no,
#         #     jenkins_cache=json.dumps(jenkins_data),
#         #     status=build_status,
#         #     created_date=created_date,
#         # )
#         # print "Added build", build
#     else:
#         build.jenkins_cache = json.dumps(jenkins_data)
#         build.status = build_status
#         build.jenkins_build_no = build_no
#         db.session.add(build)
#         db.session.commit()
#         logging.info("Synced build %r", build)

#     Build.publish_update(build)
#     return build


class JenkinsBuilder(BaseBackend):
    def __init__(self, base_url=None, *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['JENKINS_URL']

    def _get_response(self, path):
        url = '{}/{}/api/json'.format(self.base_url, path.strip('/'))
        resp = requests.get(url)
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
        # TODO(dcramer): we use a serial cursor here that doesnt account for gaps

        entity = project.get_entity('jenkins')
        job_name = entity.data['job_name']
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
            build_id_map[params['CHANGES_BID']] = item

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

    def create_build(self, build):
        entity = build.project.get_entity('jenkins')
        job_name = entity.data['job_name']

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
