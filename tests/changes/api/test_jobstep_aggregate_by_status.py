import datetime

from urllib import urlencode

from changes.testutils import APITestCase
from changes.constants import Status


class JobStepAggregateByStatusTest(APITestCase):
    path = '/api/0/jobsteps/aggregate_by_status/'

    def get(self, **kwargs):
        query_string = '?' + urlencode(kwargs) if kwargs else ''
        return self.client.get(self.path + query_string)

    def test_get(self):
        project_1 = self.create_project(slug="project_1")
        build_1 = self.create_build(project_1)
        job_1 = self.create_job(build_1)
        jobphase_1 = self.create_jobphase(job_1)

        project_2 = self.create_project(slug="project_2")
        build_2 = self.create_build(project_2)
        job_2 = self.create_job(build_2)
        jobphase_2 = self.create_jobphase(job_2)

        now = datetime.datetime.now()
        jobstep_unknown = self.create_jobstep(
            jobphase_1,
            status=Status.unknown,
            date_created=now,
            cluster="cluster_a")
        jobstep_queued = self.create_jobstep(
            jobphase_2,
            status=Status.queued,
            date_created=now,
            cluster="cluster_a")
        jobstep_in_progress = self.create_jobstep(
            jobphase_1,
            status=Status.in_progress,
            date_created=now,
            cluster="cluster_a")
        jobstep_finished = self.create_jobstep(
            jobphase_2,
            status=Status.finished,
            date_created=now,
            cluster="cluster_b")
        jobstep_collecting_results = self.create_jobstep(
            jobphase_1,
            status=Status.collecting_results,
            date_created=now,
            cluster="cluster_b")
        jobstep_allocated_ = self.create_jobstep(
            jobphase_2,
            status=Status.allocated,
            date_created=now,
            cluster="cluster_b")
        jobstep_pending_allocation = self.create_jobstep(
            jobphase_1,
            status=Status.pending_allocation,
            date_created=now,
            cluster="cluster_c")

        now_iso = now.isoformat()
        expected_output = {
            'jobsteps': {
                'by_cluster': {
                    "cluster_a": {
                        Status.queued.name:
                            [1, now_iso, jobstep_queued.id.get_hex()],
                        Status.in_progress.name:
                            [1, now_iso, jobstep_in_progress.id.get_hex()],
                    },
                    "cluster_c": {
                        Status.pending_allocation.name:
                            [1, now_iso, jobstep_pending_allocation.id.get_hex()],
                    },
                },
                'by_project': {
                    project_1.slug: {
                        Status.in_progress.name:
                            [1, now_iso, jobstep_in_progress.id.get_hex()],
                        Status.pending_allocation.name:
                            [1, now_iso, jobstep_pending_allocation.id.get_hex()],
                    },
                    project_2.slug: {
                        Status.queued.name:
                            [1, now_iso, jobstep_queued.id.get_hex()],
                    },
                },
                'global': {
                    Status.queued.name:
                        [1, now_iso, jobstep_queued.id.get_hex()],
                    Status.in_progress.name:
                        [1, now_iso, jobstep_in_progress.id.get_hex()],
                    Status.pending_allocation.name:
                        [1, now_iso, jobstep_pending_allocation.id.get_hex()],
                },
            }
        }

        # Execute the request..
        raw_resp = self.get()
        assert raw_resp.status_code == 200
        response_data = self.unserialize(raw_resp)

        # Check some keys individually, to make debugging/diffing easier if
        # there's a problem.
        expected_jobsteps = expected_output['jobsteps']
        received_jobsteps = response_data['jobsteps']
        for key, expected_value in expected_jobsteps.iteritems():
            assert received_jobsteps[key] == expected_value

        # But also check everything all together, to catch any errors that
        # slipped through the previous not-quite-rigorous asserts.
        assert response_data == expected_output
