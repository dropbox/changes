from __future__ import absolute_import, division

import json
import logging
import random
import re
import requests
import sys
import time
import uuid

from cStringIO import StringIO
from contextlib import closing
from datetime import datetime
from flask import current_app
from lxml import etree, objectify

from changes.artifacts.coverage import CoverageHandler
from changes.artifacts.dummylogfile import DummyLogFileHandler
from changes.artifacts.manager import Manager
from changes.artifacts.manifest_json import ManifestJsonHandler
from changes.artifacts.xunit import XunitHandler
from changes.backends.base import BaseBackend, UnrecoverableException
from changes.buildsteps.base import BuildStep
from changes.config import db, redis, statsreporter
from changes.constants import Result, Status
from changes.db.utils import create_or_update, get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import (
    Artifact, Cluster, ClusterNode, FailureReason, LogSource,
    LogChunk, Node, JobPhase, JobStep, LOG_CHUNK_SIZE
)
from changes.utils.http import build_uri
from changes.utils.text import chunked


RESULT_MAP = {
    'SUCCESS': Result.passed,
    'ABORTED': Result.aborted,
    'FAILURE': Result.failed,
    'REGRESSION': Result.failed,
    'UNSTABLE': Result.failed,
}

QUEUE_ID_XPATH = '/queue/item[action/parameter/name="CHANGES_BID" and action/parameter/value="{job_id}"]/id'
BUILD_ID_XPATH = ('/freeStyleProject/build[action/parameter/name="CHANGES_BID" and '
                  'action/parameter/value="{job_id}"]/number')

ID_XML_RE = re.compile(r'<id>(\d+)</id>')

LOG_SYNC_TIMEOUT_SECS = 30

# Redis key for storing the master blacklist set
# The blacklist is used to temporarily remove jenkins masters from the pool of available masters.
MASTER_BLACKLIST_KEY = 'jenkins_master_blacklist'


class NotFound(Exception):
    """Indicates a 404 response from the Jenkins API."""
    pass


class JenkinsBuilder(BaseBackend):

    def __init__(self, master_urls=None, diff_urls=None, job_name=None,
                 auth_keyname=None, verify=True,
                 cluster=None, debug_config=None,
                 *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.master_urls = master_urls
        self.diff_urls = diff_urls

        assert self.master_urls, 'No Jenkins masters specified'

        self.logger = logging.getLogger('jenkins')
        self.job_name = job_name
        self.http_session = requests.Session()
        self.auth = self.app.config[auth_keyname] if auth_keyname else None
        self.verify = verify
        self.cluster = cluster
        self.debug_config = debug_config or {}

        def report_response_status(r, *args, **kwargs):
            statsreporter.stats().incr('jenkins_api_response_{}'.format(r.status_code))

        self.http_session.hooks['response'].append(report_response_status)

    def _get_text_response(self, master_base_url, path, method='GET',
                           params=None, data=None):
        """Make an HTTP request and return a text response.

        Params:
            master_base_url (str): Jenkins master URL, in scheme://host form.
            path (str): URL path on the master to access.
            method (str): HTTP verb to use; Either 'GET' or 'POST'; 'GET' is the default.
            params (dict): Optional dictionary of URL parameters to append to the URL.
            data (dict): Optional body to attach to the request. If a dict is provided, it will be form-encoded.
        Returns:
            Content of the response, in unicode.
        Raises:
            NotFound if the server responded with a 404 status.
            Exception for other error status codes.
        """
        url = '{}/{}'.format(master_base_url, path.lstrip('/'))

        if params is None:
            params = {}

        self.logger.info('Fetching %r', url)
        resp = getattr(self.http_session, method.lower())(url, params=params,
                                                          data=data,
                                                          allow_redirects=False,
                                                          timeout=30,
                                                          auth=self.auth,
                                                          verify=self.verify)

        if resp.status_code == 404:
            raise NotFound
        elif not (200 <= resp.status_code < 400):
            exception_msg = 'Invalid response. Status code for %s was %s'
            attrs = url, resp.status_code
            self.logger.exception(exception_msg, *attrs)
            raise Exception(exception_msg % attrs)

        return resp.text

    def _get_json_response(self, master_base_url, path):
        """Makes a Jenkins API request and returns the JSON response

        Args:
            master_base_url (str): Jenkins master URL, in scheme://host form.
            path (str): URL path on the master to access.
        Returns:
            Parsed JSON from the request.
        Raises:
            NotFound if the server responded with a 404 status.
            Exception for other error status codes.
            ValueError if the response wasn't valid JSON.
        """
        path = '{}/api/json/'.format(path.strip('/'))
        text = self._get_text_response(master_base_url, path, method='GET')
        return json.loads(text)

    def _parse_parameters(self, json):
        params = {}
        for action in json['actions']:
            params.update(
                (p['name'], p.get('value'))
                for p in action.get('parameters', [])
            )
        return params

    def _create_job_step(self, phase, data, force_create=False, cluster=None, **defaults):
        """
        Gets or creates the primary JobStep for a Jenkins Job.

        Args:
            phase (JobPhase): JobPhase the JobStep should be part of.
            data (dict): JSON-serializable data associated with the Jenkins build.
            force_create (bool): Force this JobStep to be created (rather than
                retrieved). This is used when replacing a JobStep to make sure
                we don't just get the old one.
            cluster (Optional[str]): Cluster in which the JobStep will be run.
        Returns:
            JobStep: The JobStep that was retrieved or created.
        """
        defaults['data'] = data
        if cluster:
            defaults['cluster'] = cluster

        # TODO(kylec): Get rid of the kwargs.
        if not defaults.get('label'):
            # we update this once we have the build_no for this jobstep
            defaults['label'] = '<Creating Jenkins build>'

        where = {
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
        }
        if force_create:
            # uuid is unique which forces jobstep to be created
            where['id'] = uuid.uuid4()

        step, created = get_or_create(JobStep, where=where, defaults=defaults)
        assert created or not force_create
        BuildStep.handle_debug_infra_failures(step, self.debug_config, 'primary')

        return step

    def fetch_artifact(self, jobstep, artifact_data):
        """
        Fetch an artifact from a Jenkins job.

        Args:
            jobstep (JobStep): The JobStep associated with the artifact.
            artifact_data (dict): Jenkins job artifact metadata dictionary.
        Returns:
            A streamed requests Response object.
        Raises:
            HTTPError: if the response code didn't indicate success.
            Timeout: if the server took too long to respond.
        """
        url = '{base}/job/{job}/{build}/artifact/{artifact}'.format(
            base=jobstep.data['master'],
            job=jobstep.data['job_name'],
            build=jobstep.data['build_no'],
            artifact=artifact_data['relativePath'],
        )
        return self._streaming_get(url)

    def sync_artifact(self, artifact):
        jobstep = artifact.step
        resp = self.fetch_artifact(jobstep, artifact.data)

        step_id = jobstep.id.hex

        # NB: Accessing Response.content results in the entire artifact
        # being loaded into memory.
        artifact.file.save(
            StringIO(resp.content), '{0}/{1}/{2}_{3}'.format(
                step_id[:4], step_id[4:], artifact.id.hex, artifact.name
            )
        )

        # commit file save regardless of whether handler is successful
        db.session.commit()

        # TODO(dcramer): requests doesnt seem to provide a non-binary file-like
        # API, so we're stuffing it into StringIO
        try:
            self.get_artifact_manager(jobstep).process(artifact, StringIO(resp.content))
        except Exception:
            self.logger.exception(
                'Failed to sync test results for job step %s', jobstep.id)

    def _sync_log(self, jobstep, name, job_name, build_no):
        job = jobstep.job
        logsource, created = get_or_create(LogSource, where={
            'name': name,
            'step': jobstep,
        }, defaults={
            'job': job,
            'project': jobstep.project,
            'date_created': jobstep.date_started,
        })
        if created:
            offset = 0
        else:
            offset = jobstep.data.get('log_offset', 0)

        url = '{base}/job/{job}/{build}/logText/progressiveText/'.format(
            base=jobstep.data['master'],
            job=job_name,
            build=build_no,
        )

        start_time = time.time()

        with closing(self._streaming_get(url, params={'start': offset})) as resp:
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

                if time.time() > start_time + LOG_SYNC_TIMEOUT_SECS:
                    warning = ("\nTRUNCATED LOG: TOOK TOO LONG TO DOWNLOAD FROM JENKINS. SEE FULL LOG AT "
                               "{base}/job/{job}/{build}/consoleText\n").format(
                                   base=jobstep.data['master'],
                                   job=job_name,
                                   build=build_no)
                    create_or_update(LogChunk, where={
                        'source': logsource,
                        'offset': offset,
                    }, values={
                        'job': job,
                        'project': job.project,
                        'size': len(warning),
                        'text': warning,
                    })
                    offset += chunk_size
                    self.logger.warning('log download took too long: %s', logsource.get_url())
                    break

            # Jenkins will suggest to us that there is more data when the job has
            # yet to complete
            has_more = resp.headers.get('X-More-Data') == 'true'

        # We **must** track the log offset externally as Jenkins embeds encoded
        # links and we cant accurately predict the next `start` param.
        jobstep.data['log_offset'] = log_length
        db.session.add(jobstep)

        return True if has_more else None

    def _pick_master(self, job_name, is_diff=False):
        """
        Identify a master to run the given job on.

        The master with the lowest queue for the given job is chosen. By random
        sorting the first empty queue will be prioritized.
        """
        candidate_urls = self.master_urls
        if is_diff and self.diff_urls:
            candidate_urls = self.diff_urls

        blacklist = redis.smembers(MASTER_BLACKLIST_KEY)
        master_urls = [c for c in candidate_urls if c not in blacklist]

        if len(master_urls) == 0:
            raise ValueError("No masters to pick from.")

        if len(master_urls) == 1:
            return master_urls[0]

        random.shuffle(master_urls)

        best_match = (sys.maxint, None)
        for url in master_urls:
            try:
                queued_jobs = self._count_queued_jobs(url, job_name)
            except:
                self.logger.exception("Couldn't count queued jobs on master %s", url)
                continue

            if queued_jobs == 0:
                return url

            if best_match[0] > queued_jobs:
                best_match = (queued_jobs, url)

        best = best_match[1]
        if not best:
            raise Exception("Unable to successfully pick a master from {}.".format(master_urls))
        return best

    def _count_queued_jobs(self, master_base_url, job_name):
        response = self._get_json_response(
            master_base_url=master_base_url,
            path='/queue/',
        )
        return sum((
            1 for i in response['items']
            if i['task']['name'] == job_name
        ))

    def _find_job(self, master_base_url, job_name, changes_bid):
        """
        Given a job identifier, we attempt to poll the various endpoints
        for a limited amount of time, trying to match up either a queued item
        or a running job that has the CHANGES_BID parameter.

        This is necessary because Jenkins does not give us any identifying
        information when we create a job initially.

        The changes_bid parameter should be the corresponding value to look for in
        the CHANGES_BID parameter.

        The result is a mapping with the following keys:

        - queued: is it currently present in the queue
        - item_id: the queued item ID, if available
        - build_no: the build number, if available
        """
        # Check the queue first to ensure that we don't miss a transition
        # from queue -> active jobs
        item_id = self._find_queue_item_id(master_base_url, changes_bid)
        build_no = None
        if item_id:
            # Saw it in the queue, so we don't know the build number yet.
            build_no = None
        else:
            # Didn't see it in the queue, look for the build number on the assumption that it has begun.
            build_no = self._find_build_no(master_base_url, job_name, changes_bid)

        if build_no or item_id:
            # If we found either, we know the Jenkins build exists and we can probably find it again.
            return {
                'job_name': job_name,
                'queued': bool(item_id),
                'item_id': item_id,
                'build_no': build_no,
                'uri': None,
            }
        return None

    def _find_queue_item_id(self, master_base_url, changes_bid):
        """Looks in a Jenkins master's queue for an item, and returns the ID if found.
        Args:
            master_base_url (str): Jenkins master URL, in scheme://host form.
            changes_bid (str): The identifier for this Jenkins build, typically the JobStep ID.
        Returns:
            str: Queue item id if found, otherwise None.
        """
        xpath = QUEUE_ID_XPATH.format(job_id=changes_bid)
        try:
            response = self._get_text_response(
                master_base_url=master_base_url,
                path='/queue/api/xml/',
                params={
                    'xpath': xpath,
                    'wrapper': 'x',
                },
            )
        except NotFound:
            return None

        # it's possible that we managed to create multiple jobs in certain
        # situations, so let's just get the newest one
        try:
            match = etree.fromstring(response).iter('id').next()
        except StopIteration:
            return None
        return match.text

    def _find_build_no(self, master_base_url, job_name, changes_bid):
        """Looks in a Jenkins master's list of current/recent builds for one with the given CHANGES_BID,
        and returns the build number if found.

        Args:
            master_base_url (str): Jenkins master URL, in scheme://host form.
            job_name (str): Name of the Jenkins project/job to look for the build in; ex: 'generic_build'.
            changes_bid (str): The identifier for this Jenkins build, typically the JobStep ID.
        Returns:
            str: build number of the build if found, otherwise None.
        """
        xpath = BUILD_ID_XPATH.format(job_id=changes_bid)
        try:
            response = self._get_text_response(
                master_base_url=master_base_url,
                path='/job/{job_name}/api/xml/'.format(job_name=job_name),
                params={
                    'depth': 1,
                    'xpath': xpath,
                    'wrapper': 'x',
                },
            )
        except NotFound:
            return None

        # it's possible that we managed to create multiple jobs in certain
        # situations, so let's just get the newest one
        try:
            match = etree.fromstring(response).iter('number').next()
        except StopIteration:
            return None
        return match.text

    def _get_node(self, master_base_url, label):
        node, created = get_or_create(Node, {'label': label})
        if not created:
            return node

        try:
            response = self._get_text_response(
                master_base_url=master_base_url,
                path='/computer/{}/config.xml'.format(label),
            )
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
        try:
            item = self._get_json_response(
                step.data['master'],
                '/queue/item/{}'.format(step.data['item_id']),
            )
        except NotFound:
            # The build might've left the Jenkins queue since we last checked; look for the build_no of the
            # running build.
            build_no = self._find_build_no(step.data['master'], step.data['job_name'], changes_bid=step.id.hex)
            if build_no:
                step.data['queued'] = False
                step.data['build_no'] = build_no
                db.session.add(step)
                self._sync_step_from_active(step)
                return

            step.status = Status.finished
            step.result = Result.infra_failed
            db.session.add(step)
            self.logger.exception("Queued step not found in queue: {} (build: {})".format(step.id, step.job.build_id))
            statsreporter.stats().incr('jenkins_item_not_found_in_queue')
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
            self._sync_step_from_active(step)
            return

    def _get_jenkins_job(self, step):
        try:
            job_name = step.data['job_name']
            build_no = step.data['build_no']
        except KeyError:
            raise UnrecoverableException('Missing Jenkins job information')

        try:
            return self._get_json_response(
                step.data['master'],
                '/job/{}/{}'.format(job_name, build_no),
            )
        except NotFound:
            raise UnrecoverableException('Unable to find job in Jenkins')

    def _sync_step_from_active(self, step):
        item = self._get_jenkins_job(step)

        if not step.data.get('uri'):
            step.data['uri'] = item['url']

        # TODO(dcramer): we're doing a lot of work here when we might
        # not need to due to it being sync'd previously
        node = self._get_node(step.data['master'], item['builtOn'])

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

        if step.status == Status.finished:
            self._sync_results(step, item)

        if db.session.is_modified(step):
            db.session.add(step)
            db.session.commit()

    def _sync_results(self, step, item):
        job_name = step.data['job_name']
        build_no = step.data['build_no']

        artifacts = item.get('artifacts', ())

        # Detect and warn if there are duplicate artifact file names as we were relying on
        # uniqueness before.
        artifact_filenames = set()
        for artifact in artifacts:
            if artifact['fileName'] in artifact_filenames:
                self.logger.warning('Duplicate artifact filename found: %s', artifact['fileName'])
            artifact_filenames.add(artifact['fileName'])

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

    def verify_final_artifacts(self, step, artifacts):
        # If the Jenkins run was aborted or timed out, we don't expect a manifest file.
        if (step.result != Result.aborted and
            not step.data.get('timed_out', False) and
                not any(ManifestJsonHandler.can_process(a.name) for a in artifacts)):
            db.session.add(FailureReason(
                step_id=step.id,
                job_id=step.job.id,
                build_id=step.job.build_id,
                project_id=step.job.project_id,
                reason='missing_manifest_json',
            ))
            step.result = Result.infra_failed
            db.session.add(step)
            db.session.commit()

    def _get_artifact_path(self, artifact_data):
        """Given the artifact's info from Jenkins, return a relative path
        to be used as a unique name in the database.

        This assumes that Jenkins is set up to collect artifacts from a directory
        named "artifacts" if Jenkins says the relative path starts with "artifacts/".
        In those cases, remove the "artifacts/" prefix.
        """
        artifact_dir = 'artifacts/'
        if artifact_data['relativePath'].startswith(artifact_dir):
            return artifact_data['relativePath'][len(artifact_dir):]
        return artifact_data['relativePath']

    def _handle_generic_artifact(self, jobstep, artifact):
        artifact, created = get_or_create(Artifact, where={
            'step': jobstep,
            'name': self._get_artifact_path(artifact),
        }, defaults={
            'project': jobstep.project,
            'job': jobstep.job,
            'data': artifact,
        })
        if not created:
            db.session.commit()

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
        if step.data.get('generated'):
            return

        if step.data.get('queued'):
            self._sync_step_from_queue(step)
        else:
            self._sync_step_from_active(step)

    def cancel_step(self, step):
        # The Jenkins build_no won't exist if the job is still queued.
        if step.data.get('build_no'):
            url = '/job/{}/{}/stop/'.format(
                step.data['job_name'], step.data['build_no'])
        elif step.data.get('item_id'):
            url = '/queue/cancelItem?id={}'.format(step.data['item_id'])
        else:
            url = None

        step.status = Status.finished
        step.result = Result.aborted
        step.date_finished = datetime.utcnow()
        db.session.add(step)
        db.session.flush()

        if not url:
            # We don't know how to cancel the step or even if it is running, so
            # we've done all we can.
            return

        try:
            self._get_text_response(
                master_base_url=step.data['master'],
                path=url,
                method='POST',
            )
        except NotFound:
            return
        except Exception:
            self.logger.exception('Unable to cancel build upstream')

        # If the build timed out and is in progress (off the Jenkins queue),
        # try to grab the logs.
        if not step.data.get('queued') and step.data.get('timed_out', False):
            try:
                job_name = step.data['job_name']
                build_no = step.data['build_no']
                self._sync_log(
                    jobstep=step,
                    name=step.label,
                    job_name=job_name,
                    build_no=build_no,
                )
            except Exception:
                self.logger.exception(
                    'Unable to fully sync console log for job step %r',
                    step.id.hex)

    def get_job_parameters(self, job, changes_bid):
        # TODO(kylec): Take a Source rather than a Job; we don't need a Job.
        """
        Args:
            job (Job): Job to use.
            changes_bid (str): Changes BID; typically JobStep ID.

        Returns:
            dict: Parameters to be supplied to Jenkins for the job.
        """
        params = {'CHANGES_BID': changes_bid}

        source = job.build.source

        if source.revision_sha:
            params['REVISION'] = source.revision_sha

        if source.patch:
            params['PATCH_URL'] = build_uri('/api/0/patches/{0}/?raw=1'.format(
                        source.patch.id.hex))

        phab_diff_id = source.data.get('phabricator.diffID')
        if phab_diff_id:
            params['PHAB_DIFF_ID'] = phab_diff_id

        phab_revision_id = source.data.get('phabricator.revisionID')
        if phab_revision_id:
            params['PHAB_REVISION_ID'] = phab_revision_id

        if self.cluster:
            params['CLUSTER'] = self.cluster

        return params

    def create_jenkins_job_from_params(self, changes_bid, params, job_name=None, is_diff=False):
        if job_name is None:
            job_name = self.job_name

        if not job_name:
            raise UnrecoverableException('Missing Jenkins project configuration')

        json_data = {
            'parameter': params
        }

        master = self._pick_master(job_name, is_diff)

        # TODO: Jenkins will return a 302 if it cannot queue the job which I
        # believe implies that there is already a job with the same parameters
        # queued.
        self._get_text_response(
            master_base_url=master,
            path='/job/{}/build'.format(job_name),
            method='POST',
            data={
                'json': json.dumps(json_data),
            },
        )

        # we retry for a period of time as Jenkins doesn't have strong consistency
        # guarantees and the job may not show up right away
        t = time.time() + 5
        job_data = None
        while time.time() < t:
            job_data = self._find_job(master, job_name, changes_bid)
            if job_data:
                break
            time.sleep(0.3)

        if job_data is None:
            raise Exception('Unable to find matching job after creation. GLHF')

        job_data['master'] = master

        return job_data

    def get_default_job_phase_label(self, job, job_name):
        return 'Build {0}'.format(job_name)

    def create_job(self, job, replaces=None):
        """
        Creates a job within Jenkins.

        Due to the way the API works, this consists of two steps:

        - Submitting the job
        - Polling for the newly created job to associate either a queue ID
          or a finalized build number.
        """
        phase, created = get_or_create(JobPhase, where={
            'job': job,
            'label': self.get_default_job_phase_label(job, self.job_name),
            'project': job.project,
        }, defaults={
            'status': job.status,
        })
        assert not created or not replaces

        step = self._create_job_step(
            phase=phase,
            data={'job_name': self.job_name},
            status=job.status,
            force_create=bool(replaces),
            cluster=self.cluster
        )

        if replaces:
            replaces.replacement_id = step.id
            db.session.add(replaces)

        db.session.commit()

        # now create the jenkins build

        # we don't commit immediately because we also want to update the job
        # and jobstep using the job_data we get from jenkins
        job_data = self.create_jenkins_build(step, commit=False)
        if job_data['queued']:
            job.status = Status.queued
        else:
            job.status = Status.in_progress
        db.session.add(job)

        assert 'master' in step.data
        assert 'job_name' in step.data
        assert 'build_no' in step.data or 'item_id' in step.data
        # now we have the build_no/item_id and can set the full jobstep label
        step.label = '{0} #{1}'.format(step.data['job_name'], step.data['build_no'] or step.data['item_id'])
        db.session.add(step)

        db.session.commit()

        sync_job_step.delay(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        return step

    def create_jenkins_build(self, step, job_name=None, commit=True, **kwargs):
        """
        Create a jenkins build for the given jobstep.

        If the given step already has a jenkins build associated with it, this
        will not perform any work. If not, this creates the build, updates the
        step to refer to the new build, optionally committing these changes.

        Args:
            step (JobStep): The shard we'd like to launch a jenkins build for.
            job_name (str): Job's name. Default is self.job_name.
            commit (bool): Whether to commit changes to database at the end.
            kwargs: Additional arguments to be passed to get_job_parameters()
        """
        if step.data.get('build_no') or step.data.get('item_id'):
            return

        params_dict = self.get_job_parameters(step.job, changes_bid=step.id.hex, **kwargs)
        jenkins_params = [{'name': k, 'value': v} for k, v in params_dict.iteritems()]

        is_diff = not step.job.source.is_commit()
        job_data = self.create_jenkins_job_from_params(
            changes_bid=step.id.hex,
            params=jenkins_params,
            job_name=job_name,
            is_diff=is_diff
        )
        step.data.update(job_data)
        db.session.add(step)

        # Hook that allows other builders to add commands for the jobstep
        # which tells changes-client what to run.
        # TODO(kylec): Stop passing the params as env once the data is available
        # in changes-client by other means.
        self.create_commands(step, env=params_dict)

        if commit:
            db.session.commit()

        return job_data

    def get_artifact_manager(self, jobstep):
        handlers = [CoverageHandler, XunitHandler, ManifestJsonHandler]
        if self.debug_config.get('fetch_jenkins_logs'):
            handlers.append(DummyLogFileHandler)
        return Manager(handlers)

    def create_commands(self, step, env):
        """
        Args:
            step (JobStep): The JobStep to create commands under.
            env (dict): Environment variables for the commands.
        """
        pass

    def can_snapshot(self):
        return False

    def _streaming_get(self, url, params=None):
        """
        Perform an HTTP GET request with a streaming response.

        Args:
            url (str): The url to fetch.
            params (dict): Optional dictionary of query parameters.
        Returns:
            A streamed requests Response object.
        Raises:
            HTTPError: if the response code didn't indicate success.
            Timeout: if the server took too long to respond.
        """
        resp = self.http_session.get(url, stream=True, timeout=15,
                                     params=params, auth=self.auth,
                                     verify=self.verify)
        resp.raise_for_status()
        return resp
