import logging
import json
import random as insecure_random
import requests
import dateutil.parser
import time
from base64 import b64encode

from cStringIO import StringIO

DEFAULT_TIMEOUT_SEC = 15
MAX_RETRIES = 5
RETRY_SLEEP_MSEC = 1000


def is_error(resp):
    return not resp.ok


# We use 4XX status codes to indicate client request is wrong. No point retrying.
def is_terminal_error(resp):
    return is_error(resp) and resp.status_code < 500


def is_retriable_error(resp):
    return is_error(resp) and resp.status_code >= 500


# Copied from artifactstore server, see go server for documentation
class BucketState:
    UNKNOWN = 0

    # Accepting new artifacts and appends to existing artifacts
    OPEN = 1

    # No further changes to this bucket. No new artifacts or appends to existing ones.
    CLOSED = 2

    # Similar to `CLOSED`. Was forcibly closed because it was not explicitly closed before deadline.
    TIMEDOUT = 3


class ArtifactState:
    UNKNOWN_ARTIFACT_STATE = 0

    # Error during streamed upload.
    ERROR = 1

    # Log file being streamed in chunks. We currently store them as LogChunks.
    APPENDING = 2

    # Once the artifact has been finalized (or the bucket closed), the artifact which was being
    # appended will be marked for compaction and upload to S3.
    APPEND_COMPLETE = 3

    # The artifact is waiting for a file upload request to stream through to S3.
    WAITING_FOR_UPLOAD = 4

    # If the artifact is in LogChunks, it is now being merged and uploaded to S3.
    # Else, the file is being passed through to S3 directly from the client.
    UPLOADING = 5

    # Terminal state: the artifact is in S3 in its entirety.
    UPLOADED = 6

    # Deadline exceeded before APPEND_COMPLETE OR UPLOADED
    DEADLINE_EXCEEDED = 7

    # Artifact was closed without any appends or upload operation.
    CLOSED_WITHOUT_DATA = 8


class Bucket(object):
    def __init__(self, bucket_dict):
        self.name = bucket_dict['id']
        self.owner = bucket_dict['owner']
        self.state = bucket_dict['state']
        self.date_created = dateutil.parser.parse(bucket_dict['dateCreated'])
        self.date_closed = dateutil.parser.parse(bucket_dict['dateClosed'])


class Artifact(object):
    def __init__(self, artifact_dict):
        self.name = artifact_dict['name']
        self.bucket_name = artifact_dict['bucketId']
        self.state = artifact_dict['state']
        self.path = artifact_dict['relativePath']
        self.size = artifact_dict['size']
        self.s3URL = artifact_dict['s3URL']
        self.deadline_mins = artifact_dict['deadlineMins']
        self.date_created = dateutil.parser.parse(artifact_dict['dateCreated'])


class ArtifactStoreClient:
    # TODO (if necessary): Implement get_artifact_chunks to fetch chunks as they upload

    def __init__(self, server):
        self._server = server
        self._logger = logging.getLogger('artifactstore')
        self._session = requests.Session()

    # Returns the response object or raises an exception
    def _simple_retry_request(self, method, rel_url,
                              max_retries=MAX_RETRIES,
                              sleep_msecs_between_retries=RETRY_SLEEP_MSEC, randomize_sleep=True,
                              timeout=DEFAULT_TIMEOUT_SEC,
                              **kwargs):
        # We don't support indefinite retries
        assert max_retries != 0

        attempt = 0
        while attempt < MAX_RETRIES:
            # If func_to_retry throws, we treat it as a failure and retry
            try:
                resp = self._session.request(method, self._server + rel_url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                self._logger.warning('Caught error %s' % (e))

                attempt += 1
                if attempt >= MAX_RETRIES:
                    raise e

                if isinstance(e, requests.HTTPError) and not is_retriable_error(e.response):
                    raise e

                sleep_msecs = sleep_msecs_between_retries

                if randomize_sleep:
                    sleep_msecs = insecure_random.randint(0, sleep_msecs)

                self._logger.debug('Sleeping %d msecs before attempt #%d' % (sleep_msecs, attempt + 1))
                time.sleep((sleep_msecs / 1000.0))

        raise "Too many retries!"

    def list_buckets(self):
        """
        :return: List of Buckets
        """
        return [Bucket(b) for b in self._simple_retry_request('get', '/buckets').json()]

    def create_bucket(self, bucket_name, owner='changes'):
        """
        :return: The created Bucket
        """
        return Bucket(
            self._simple_retry_request('post', '/buckets/',
                                       data=json.dumps({'id': bucket_name, 'owner': owner}))
                .json()
        )

    def close_bucket(self, bucket_name):
        """
        Closes the bucket, preventing any updates to the bucket. Also closes all open artifacts in the bucket.

        :return: The closed Bucket
        """
        return Bucket(
            self._simple_retry_request('post', '/buckets/%s/close' % (bucket_name))
                .json()
        )

    def get_bucket(self, bucket_name):
        return Bucket(
            self._simple_retry_request('get', '/buckets/%s' % (bucket_name))
                .json()
        )

    def list_artifacts(self, bucket_name):
        """
        Gets a list of all artifacts in a bucket

        :return: List of Artifacts
        """
        return [Artifact(a) for a in self._simple_retry_request('get', '/buckets/%s/artifacts/' % (bucket_name)).json()]

    def create_chunked_artifact(self, bucket_name, artifact_name):
        """
        Creates a chunked artifact.
        IMPORTANT: the name of the artifact may not match the given name, due to server-side de-duplication

        :return: The created Artifact
        """
        return Artifact(
            self._simple_retry_request('post', '/buckets/%s/artifacts' % (bucket_name),
                                       data=json.dumps({'name': artifact_name, 'chunked': True}))
                .json()
        )

    def post_artifact_chunk(self, bucket_name, artifact_name, offset, chunk):
        """
        Writes to a chunked artifact

        :return: The updated Artifact
        """
        return Artifact(
            self._simple_retry_request('post', '/buckets/%s/artifacts/%s' % (bucket_name, artifact_name),
                                       data=json.dumps({
                                           'size': len(chunk),
                                           'byteoffset': offset,
                                           'bytes': b64encode(chunk)
                                       }),
                                       randomize_sleep=False)
                .json()
        )

    def close_chunked_artifact(self, bucket_name, artifact_name):
        """
        Closes a chunked artifact
        """
        self._simple_retry_request('post', '/buckets/%s/artifacts/%s/close' % (bucket_name, artifact_name))

    def write_streamed_artifact(self, bucket_name, artifact_name, data, path=None):
        """
        Creates and posts a streamed artifact
        IMPORTANT: the name of the artifact may not match the given name, due to server-side de-duplication

        :param path: Original path of file
        :return: The written Artifact
        """
        # No path defaults to the artifact name
        path = path or artifact_name
        artifact = Artifact(
            self._simple_retry_request('post', '/buckets/%s/artifacts' % (bucket_name),
                                       data=json.dumps({
                                           'name': artifact_name,
                                           'chunked': False,
                                           'size': len(data),
                                           'relativePath': path
                                       }))
                .json()
        )
        # Change the name to account for server-side de-duplication
        artifact_name = artifact.name

        return Artifact(
            self._simple_retry_request('post', '/buckets/%s/artifacts/%s' % (bucket_name, artifact_name), data=data)
                .json()
        )

    def get_artifact(self, bucket_name, artifact_name):
        return Artifact(
            self._simple_retry_request('get', '/buckets/%s/artifacts/%s' % (bucket_name, artifact_name))
                .json()
        )

    def get_artifact_content(self, bucket_name, artifact_name, offset=None, limit=None):
        """
        Fetches (partial) contents of an artifact from artifactstore

        :return: Artifact contents as a file (StringIO)
        """
        headers = {}
        if offset is not None:
            if limit is not None and limit >= 1:
                headers['Range'] = 'bytes=%d-%d' % (offset, offset + limit - 1)
            else:
                headers['Range'] = 'bytes=%d-' % (offset)

        return StringIO(
            self._simple_retry_request('get', '/buckets/%s/artifacts/%s/content' % (bucket_name, artifact_name),
                                       headers=headers)
                .content
        )
