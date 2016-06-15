import json
from datetime import datetime

import changes.lib.artifact_store_lib as artifact_store_lib
import pytest
import requests
import responses
from changes.testutils.cases import TestCase


class ArtifactStoreClientTestCase(TestCase):
    @responses.activate
    def test_success(self):

        client = artifact_store_lib.ArtifactStoreClient('http://artifactstore:1234')

        url_success = 'http://artifactstore:1234/buckets/abcde'
        responses.add(responses.GET, url_success,
                      body=json.dumps({
                          'dateClosed': '0001-01-01T00:00:00Z',
                          'dateCreated': '2016-06-15T01:53:07.708415Z',
                          'id': 'abcde',
                          'owner': 'changes',
                          'state': 1
                      }), status=201)

        resp = client.get_bucket('abcde')
        assert resp.name == 'abcde'

    @responses.activate
    def test_retry_server_5xx(self):

        client = artifact_store_lib.ArtifactStoreClient('http://artifactstore:1234')

        # Server errors should be retried
        url_server_error = 'http://artifactstore:1234/buckets/aaaaa'
        responses.add(responses.GET, url_server_error,
                      body='{"error": "server error"}', status=500)

        with self.assertRaises(requests.HTTPError) as cm:
            client.get_bucket('aaaaa')
        e = cm.exception
        assert e.response.status_code == 500
        assert len(responses.calls) == artifact_store_lib.MAX_RETRIES

    @responses.activate
    def test_retry_timeout(self):

        client = artifact_store_lib.ArtifactStoreClient('http://artifactstore:1234')

        # Slow servers should be retried until they pass
        url_slow_server = 'http://artifactstore:1234/buckets/bbbbb/artifacts/arti'

        # Succeed after timing out 3 times
        NUM_TIMEOUTS = 3
        timeout_counter = [0]

        def timeout_request(request):
            if timeout_counter[0] < NUM_TIMEOUTS:
                timeout_counter[0] += 1
                raise requests.Timeout()
            else:
                return 200, {}, json.dumps({
                    'bucketId': 'bbbbb',
                    'dateCreated': '2016-06-15T18:18:30.560047Z',
                    'id': 5,
                    'name': 'arti',
                    's3URL': '',
                    'size': 10,
                    'state': 6,
                    'deadlineMins': 30,
                    'relativePath': 'junit.xml'
                })

        responses.add_callback(responses.GET, url_slow_server, callback=timeout_request)

        resp = client.get_artifact('bbbbb', 'arti')
        assert resp.name == 'arti'
        assert timeout_counter[0] == NUM_TIMEOUTS
        # 1 call, as the others all raise errors and don't get recorded
        assert len(responses.calls) == 1

    @responses.activate
    def test_terminal_error(self):

        client = artifact_store_lib.ArtifactStoreClient('http://artifactstore:1234')

        url_bad_bucket = 'http://artifactstore:1234/buckets/ccccc'

        responses.add(responses.GET, url_bad_bucket,
                      body='{"error": "no such bucket"}', status=404)

        with self.assertRaises(requests.HTTPError) as cm:
            client.get_bucket('ccccc')
        e = cm.exception
        assert e.response.status_code == 404
        # Should fail immediately
        assert len(responses.calls) == 1


@pytest.mark.skipif(True, reason='needs a test artifact store at artifacts:8001')
class ArtifactStoreIntegrationTestCase(TestCase):
    def test_simple(self):
        client = artifact_store_lib.ArtifactStoreClient('http://artifacts:8001')

        bucket_name = 'jobstep-' + datetime.now().isoformat()

        client.create_bucket(bucket_name)

        # Test basic file-writing
        art1_name = 'junit.xml'
        art1_data = 'blahblahblah'
        art1_path = 'artifacts/junit.xml'

        art1 = client.write_streamed_artifact(bucket_name, art1_name, art1_data, art1_path)
        ar1_name = art1.name
        assert client.get_artifact_content(bucket_name, art1_name).read() == art1_data

        # Test chunked file writing
        art2_name = 'junit.xml'
        art2_data1 = 'Hello world!'
        art2_data2 = 'Hello world!'

        art2 = client.create_chunked_artifact(bucket_name, art2_name)
        art2_name = art2.name

        art2 = client.post_artifact_chunk(bucket_name, art2_name, offset=0, chunk=art2_data1)
        assert art2.name == art2_name

        art2 = client.post_artifact_chunk(bucket_name, art2_name, offset=len(art2_data1), chunk=art2_data2)
        assert art2.name == art2_name

        client.close_chunked_artifact(bucket_name, art2_name)
        assert client.get_artifact_content(bucket_name, art2_name).read() == art2_data1 + art2_data2

        # Ensure that streamed artifacts handle de-duplicated names properly
        art3_name = 'junit.xml'
        art3_data = 'lots of xml'
        art3_path = 'even_moar_artifacts/junit.xml'

        art3 = client.write_streamed_artifact(bucket_name, art3_name, art3_data, art3_path)
        art3_name = art3.name
        assert client.get_artifact_content(bucket_name, art3_name).read() == art3_data

        # Test closing the bucket
        client.close_bucket(bucket_name)

        with self.assertRaises(requests.HTTPError) as cm:
            client.write_streamed_artifact(bucket_name, 'adsf', 'data', 'asdf')
        assert cm.exception.response.status_code == 400
