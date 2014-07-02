import itertools

from datetime import datetime, timedelta

from changes.config import db
from changes.models import ItemStat
from changes.testutils import APITestCase


def to_timestamp(dt):
    return int(float(dt.strftime('%s.%f')) * 1000)


class ProjectDetailsTest(APITestCase):
    def test_simple(self):
        now = datetime(2014, 4, 21, 22, 15, 22)

        project = self.create_project()
        path = '/api/0/projects/{0}/stats/'.format(project.id.hex)

        build1 = self.create_build(
            project=project,
            date_created=now,
        )
        build2 = self.create_build(
            project=project,
            date_created=now - timedelta(hours=1),
        )
        build3 = self.create_build(
            project=project,
            date_created=now - timedelta(days=1),
        )
        build4 = self.create_build(
            project=project,
            date_created=now.replace(day=1) - timedelta(days=32),
        )
        build5 = self.create_build(
            project=project,
            date_created=now.replace(day=1) - timedelta(days=370),
        )

        db.session.add(ItemStat(name='test_count', value=1, item_id=build1.id))
        db.session.add(ItemStat(name='test_count', value=3, item_id=build2.id))
        db.session.add(ItemStat(name='test_count', value=6, item_id=build3.id))
        db.session.add(ItemStat(name='test_count', value=20, item_id=build4.id))
        db.session.add(ItemStat(name='test_count', value=100, item_id=build5.id))
        db.session.commit()

        base_path = path + '?from=' + now.strftime('%s') + '&'

        # test hourly
        resp = self.client.get(base_path + 'stat=test_count&resolution=1h')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 24
        assert data[0]['time'] == to_timestamp(datetime(2014, 4, 20, 22, 0))
        assert data[0]['value'] == 6
        for point in data[1:-1]:
            assert point['value'] == 0
        assert data[-1]['time'] == to_timestamp(datetime(2014, 4, 21, 21, 0))
        assert data[-1]['value'] == 3

        # test weekly
        resp = self.client.get(base_path + 'stat=test_count&resolution=1w')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 26
        for point in itertools.chain(data[:-8], data[-7:-1]):
            assert point['value'] == 0
        assert data[-8]['time'] == to_timestamp(datetime(2014, 2, 24, 0, 0))
        assert data[-8]['value'] == 20
        assert data[-1]['time'] == to_timestamp(datetime(2014, 4, 14, 0, 0))
        assert data[-1]['value'] == 6

        # test daily
        resp = self.client.get(base_path + 'stat=test_count&resolution=1d')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 30
        for point in data[:-1]:
            assert point['value'] == 0
        assert data[-1]['time'] == to_timestamp(datetime(2014, 4, 20, 0, 0))
        assert data[-1]['value'] == 6

        # test monthly
        resp = self.client.get(base_path + 'stat=test_count&resolution=1m')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 12
        for point in itertools.chain(data[:-2], data[-1:]):
            assert point['value'] == 0
        assert data[-2]['time'] == to_timestamp(datetime(2014, 2, 1, 0, 0))
        assert data[-2]['value'] == 20
