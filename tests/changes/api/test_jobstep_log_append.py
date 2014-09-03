from changes.models import LogSource, LogChunk
from changes.testutils import APITestCase


class JobStepLogAppendTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        path = '/api/0/jobsteps/{0}/logappend/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'source': 'stderr',
            'offset': 0,
            'text': 'hello world!\n',
        })

        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        logsource = LogSource.query.get(data['source']['id'])
        assert logsource.name == 'stderr'
        assert len(data['chunks']) == 1
        logchunk = LogChunk.query.get(data['chunks'][0]['id'])
        assert logchunk.offset == 0
        assert logchunk.size == 13

        # TODO(dcramer): there's an issue in flask/somewhere that a 204 causes
        # an error in the test runner
        # ensure our soft check for duplicate logs matches
        # resp = self.client.post(path, data={
        #     'source': 'stderr',
        #     'offset': 0,
        #     'text': 'hello world!\n',
        # })

        # assert resp.status_code == 200

        # resp = self.client.post(path, data={
        #     'source': 'stderr',
        #     'offset': 12,
        #     'text': 'hello world!\n',
        # })

        # assert resp.status_code == 204

        # append to existing log
        resp = self.client.post(path, data={
            'source': 'stderr',
            'offset': 13,
            'text': 'foo bar?\n',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        logsource = LogSource.query.get(data['source']['id'])
        assert logsource.name == 'stderr'
        assert len(data['chunks']) == 1
        logchunk = LogChunk.query.get(data['chunks'][0]['id'])
        assert logchunk.offset == 13
        assert logchunk.size == 9

        # create second logsource
        resp = self.client.post(path, data={
            'source': 'stdout',
            'offset': 0,
            'text': 'zoom zoom\n',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        logsource = LogSource.query.get(data['source']['id'])
        assert logsource.name == 'stdout'
        assert len(data['chunks']) == 1
        logchunk = LogChunk.query.get(data['chunks'][0]['id'])
        assert logchunk.offset == 0
        assert logchunk.size == 10

    def test_without_offsets(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        path = '/api/0/jobsteps/{0}/logappend/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'source': 'stderr',
            'text': 'hello world!\n',
        })

        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        logsource = LogSource.query.get(data['source']['id'])
        assert logsource.name == 'stderr'
        assert len(data['chunks']) == 1
        logchunk = LogChunk.query.get(data['chunks'][0]['id'])
        assert logchunk.offset == 0
        assert logchunk.size == 13

        resp = self.client.post(path, data={
            'source': 'stderr',
            'text': 'foo bar?\n',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        logsource = LogSource.query.get(data['source']['id'])
        assert logsource.name == 'stderr'
        assert len(data['chunks']) == 1
        logchunk = LogChunk.query.get(data['chunks'][0]['id'])
        assert logchunk.offset == 13
        assert logchunk.size == 9
