import datetime

from changes.testutils import APITestCase
from changes.constants import Status


class TaskStatsTest(APITestCase):
    path = '/api/0/task_stats/'

    def test_get(self):
        now = datetime.datetime.now()
        sync_job_step_finished = self.create_task(
            task_name='sync_job_step',
            status=Status.finished,
            date_created=now,
            date_modified=now)
        sync_job_in_progress = self.create_task(
            task_name='sync_job',
            status=Status.in_progress,
            num_retries=1,
            date_created=now,
            date_modified=now)
        sync_job_queued = self.create_task(
            task_name='sync_job',
            status=Status.queued,
            date_created=now,
            date_modified=now)
        sync_build_in_progress = self.create_task(
            task_name='sync_build',
            status=Status.in_progress,
            date_created=now,
            date_modified=now)
        fire_signal_queued = self.create_task(
            task_name='fire_signal',
            status=Status.queued,
            date_created=now,
            date_modified=now)

        now_iso = now.isoformat()
        expected_output = {
            'sync_job': {
                'in_progress': {
                    'count': 1,
                    'max_retries': 1,
                    'max_retries_id': sync_job_in_progress.id.get_hex(),
                    'oldest_created_time': now_iso,
                    'oldest_created_id': sync_job_in_progress.id.get_hex(),
                    'oldest_modified_time': now_iso,
                    'oldest_modified_id': sync_job_in_progress.id.get_hex(),
                },
                'queued': {
                    'count': 1,
                    'max_retries': 0,
                    'max_retries_id': sync_job_queued.id.get_hex(),
                    'oldest_created_time': now_iso,
                    'oldest_created_id': sync_job_queued.id.get_hex(),
                    'oldest_modified_time': now_iso,
                    'oldest_modified_id': sync_job_queued.id.get_hex(),
                },
                'all': {
                    'count': 2,
                    'max_retries': 1,
                    'max_retries_id': sync_job_in_progress.id.get_hex(),
                    'oldest_created_time': now_iso,
                    # id not checked: ambiguous
                    'oldest_modified_time': now_iso,
                    # id not checked: ambiguous
                },
            },
            'sync_build': {
                'in_progress': {
                    'count': 1,
                    'max_retries': 0,
                    'max_retries_id': sync_build_in_progress.id.get_hex(),
                    'oldest_created_time': now_iso,
                    'oldest_created_id': sync_build_in_progress.id.get_hex(),
                    'oldest_modified_time': now_iso,
                    'oldest_modified_id': sync_build_in_progress.id.get_hex(),
                },
                'all': {
                    'count': 1,
                    'max_retries': 0,
                    'max_retries_id': sync_build_in_progress.id.get_hex(),
                    'oldest_created_time': now_iso,
                    'oldest_created_id': sync_build_in_progress.id.get_hex(),
                    'oldest_modified_time': now_iso,
                    'oldest_modified_id': sync_build_in_progress.id.get_hex(),
                },
            },
            'fire_signal': {
                'queued': {
                    'count': 1,
                    'max_retries': 0,
                    'max_retries_id': fire_signal_queued.id.get_hex(),
                    'oldest_created_time': now_iso,
                    'oldest_created_id': fire_signal_queued.id.get_hex(),
                    'oldest_modified_time': now_iso,
                    'oldest_modified_id': fire_signal_queued.id.get_hex(),
                },
                'all': {
                    'count': 1,
                    'max_retries': 0,
                    'max_retries_id': fire_signal_queued.id.get_hex(),
                    'oldest_created_time': now_iso,
                    'oldest_created_id': fire_signal_queued.id.get_hex(),
                    'oldest_modified_time': now_iso,
                    'oldest_modified_id': fire_signal_queued.id.get_hex(),
                },
            },
            'all': {
                'in_progress': {
                    'count': 2,
                    'max_retries': 1,
                    'max_retries_id': sync_job_in_progress.id.get_hex(),
                    'oldest_created_time': now_iso,
                    # id not checked: ambiguous
                    'oldest_modified_time': now_iso,
                    # id not checked: ambiguous
                },
                'queued': {
                    'count': 2,
                    'max_retries': 0,
                    # id not checked: ambiguous
                    'oldest_created_time': now_iso,
                    # id not checked: ambiguous
                    'oldest_modified_time': now_iso,
                    # id not checked: ambiguous
                },
                'all': {
                    'count': 4,
                    'max_retries': 1,
                    'max_retries_id': sync_job_in_progress.id.get_hex(),
                    'oldest_created_time': now_iso,
                    # id not checked: ambiguous
                    'oldest_modified_time': now_iso,
                    # id not checked: ambiguous
                },
            },
        }

        raw_resp = self.client.get(self.path)
        assert raw_resp.status_code == 200
        response_data = self.unserialize(raw_resp)

        # delete ambiguous fields
        del response_data['sync_job']['all']['oldest_created_id']
        del response_data['sync_job']['all']['oldest_modified_id']
        del response_data['all']['in_progress']['oldest_created_id']
        del response_data['all']['in_progress']['oldest_modified_id']
        del response_data['all']['queued']['max_retries_id']
        del response_data['all']['queued']['oldest_created_id']
        del response_data['all']['queued']['oldest_modified_id']
        del response_data['all']['all']['oldest_created_id']
        del response_data['all']['all']['oldest_modified_id']

        assert response_data == expected_output
