from cStringIO import StringIO
from datetime import datetime
from changes.lib.artifact_store_lib import Artifact, ArtifactState, Bucket, BucketState


class ArtifactStoreMock:
    """
    Mock out the ArtifactStoreClient using in-memory dictionaries
    """

    buckets = {}            # type: Dict[str, Bucket]
    artifacts = {}          # type: Dict[str, Dict[str, Artifact]]
    artifact_content = {}   # type: Dict[str, Dict[str, str]]

    @staticmethod
    def reset():
        buckets = {}
        artifacts = {}
        artifact_content = {}

    def __init__(self, server):
        self.server = server

    def list_buckets(self):
        """
        :return: List of Buckets
        """
        return list(ArtifactStoreMock.buckets.values())

    def create_bucket(self, bucket_name, owner='changes'):
        """
        :return: The created Bucket
        """
        if bucket_name in ArtifactStoreMock.buckets:
            raise Exception('bucket already exists')

        b = Bucket(
            {
                'id': bucket_name,
                'owner': owner,
                'dateCreated': datetime.now().isoformat(),
                'dateClosed': datetime.min.isoformat(),
                'state': BucketState.OPEN
            }
        )
        ArtifactStoreMock.buckets[bucket_name] = b
        # Create an empty bucket
        ArtifactStoreMock.artifacts[bucket_name] = {}
        ArtifactStoreMock.artifact_content[bucket_name] = {}
        return b

    def close_bucket(self, bucket_name):
        """
        Closes the bucket, preventing any updates to the bucket. Also closes all open artifacts in the bucket.

        :return: The closed Bucket
        """
        b = ArtifactStoreMock.buckets[bucket_name]
        if b.state == BucketState.OPEN:
            for artifact_name in ArtifactStoreMock.artifacts[bucket_name].keys():
                self.close_chunked_artifact(bucket_name, artifact_name)
            b.date_closed = datetime.now()
            b.state = BucketState.CLOSED
            ArtifactStoreMock.buckets[bucket_name] = b
        return b

    def get_bucket(self, bucket_name):
        return ArtifactStoreMock.buckets[bucket_name]

    def list_artifacts(self, bucket_name):
        """
        Gets a list of all artifacts in a bucket

        :return: List of Artifacts
        """
        return list(ArtifactStoreMock.artifacts[bucket_name].values())

    def create_chunked_artifact(self, bucket_name, artifact_name):
        """
        Creates a chunked artifact.
        IMPORTANT: the name of the artifact may not match the given name, due to server-side de-duplication

        :return: The created Artifact
        """
        if ArtifactStoreMock.buckets[bucket_name].state != BucketState.OPEN:
            raise Exception('bucket already closed')

        while artifact_name in ArtifactStoreMock.artifacts[bucket_name]:
            artifact_name += '.dup'

        a = Artifact(
            {
                'name': artifact_name,
                'relativePath': artifact_name,
                'size': 0,
                'state': ArtifactState.APPENDING,
                'bucketId': bucket_name,
                's3URL': '/%s/%s' % (bucket_name, artifact_name),
                'dateCreated': datetime.now().isoformat(),
                'deadlineMins': 30,
            }
        )
        ArtifactStoreMock.artifacts[bucket_name][artifact_name] = a
        ArtifactStoreMock.artifact_content[bucket_name][artifact_name] = ''
        return a

    def post_artifact_chunk(self, bucket_name, artifact_name, offset, chunk):
        """
        Writes to a chunked artifact

        :return: The updated Artifact
        """
        if ArtifactStoreMock.buckets[bucket_name].state != BucketState.OPEN:
            raise Exception('bucket already closed')

        a = ArtifactStoreMock.artifacts[bucket_name][artifact_name]

        if a.state != ArtifactState.APPENDING:
            raise Exception('artifact not open for appending')

        if offset != a.size:
            raise Exception('incorrect offset!')

        ArtifactStoreMock.artifact_content[bucket_name][artifact_name] += chunk
        a.size += len(chunk)

        ArtifactStoreMock.artifacts[bucket_name][artifact_name] = a
        return a

    def close_chunked_artifact(self, bucket_name, artifact_name):
        """
        Closes a chunked artifact
        """
        if ArtifactStoreMock.buckets[bucket_name].state != BucketState.OPEN:
            raise Exception('bucket already closed')

        a = ArtifactStoreMock.artifacts[bucket_name][artifact_name]

        if a.state == ArtifactState.APPENDING:
            a.state = ArtifactState.UPLOADED

        ArtifactStoreMock.artifacts[bucket_name][artifact_name] = a

    def write_streamed_artifact(self, bucket_name, artifact_name, data, path=None):
        """
        Creates and posts a streamed artifact
        IMPORTANT: the name of the artifact may not match the given name, due to server-side de-duplication

        :param path: Original path of file
        :return: The written Artifact
        """
        if ArtifactStoreMock.buckets[bucket_name].state != BucketState.OPEN:
            raise Exception('bucket already closed')

        # No path defaults to the artifact name
        path = path or artifact_name

        while artifact_name in ArtifactStoreMock.artifacts[bucket_name]:
            artifact_name += '.dup'

        a = Artifact(
            {
                'name': artifact_name,
                'relativePath': path,
                'size': len(data),
                'state': ArtifactState.UPLOADED,
                'bucketId': bucket_name,
                's3URL': '/%s/%s' % (bucket_name, artifact_name),
                'dateCreated': datetime.now().isoformat(),
                'deadlineMins': 30,
            }
        )

        ArtifactStoreMock.artifacts[bucket_name][artifact_name] = a
        ArtifactStoreMock.artifact_content[bucket_name][artifact_name] = data

        return a

    def get_artifact(self, bucket_name, artifact_name):
        return ArtifactStoreMock.artifacts[bucket_name][artifact_name]

    def get_artifact_content(self, bucket_name, artifact_name, offset=None, limit=None):
        """
        Fetches (partial) contents of an artifact from artifactstore

        :return: Artifact contents as a file (StringIO)
        """
        start_offset, end_offset = None, None
        if offset is not None:
            start_offset = offset
            if limit is not None:
                end_offset = offset + limit

        return StringIO(ArtifactStoreMock.artifact_content[bucket_name][artifact_name][start_offset:end_offset])
