import mock

from changes.api.base import as_json
from changes.testutils import TestCase
from changes.events import publish_build_update, publish_job_update


class PublishBuildUpdateTest(TestCase):
    @mock.patch('changes.events.pubsub.publish')
    def test_simple(self, publish):
        build = self.create_build(self.project)
        json = as_json(build)

        publish_build_update(build)

        publish.assert_any_call('builds:{0}'.format(build.id.hex), {
            'data': json,
            'event': 'build.update',
        })
        publish.assert_any_call('projects:{0}:builds'.format(build.project_id.hex), {
            'data': json,
            'event': 'build.update',
        })


class PublishJobUpdateTest(TestCase):
    @mock.patch('changes.events.pubsub.publish')
    def test_simple(self, publish):
        build = self.create_build(self.project)
        job = self.create_job(build=build)
        json = as_json(job)

        publish_job_update(job)

        publish.assert_any_call('jobs:{0}'.format(job.id.hex), {
            'data': json,
            'event': 'job.update',
        })
        publish.assert_any_call('builds:{0}:jobs'.format(job.build_id.hex), {
            'data': json,
            'event': 'job.update',
        })
