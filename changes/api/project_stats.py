from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from flask.ext.restful import reqparse
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.config import db
from changes.models import Project, Build, ItemStat


STAT_CHOICES = (
    'test_count',
    'test_duration',
    'test_rerun_count',
    'tests_missing',
)

RESOLUTION_CHOICES = (
    '1h',
    '1d',
    '1w',
    '1m',
)

AGG_CHOICES = (
    'sum',
    'avg',
)

POINTS_DEFAULT = {
    '1h': 24,
    '1d': 30,
    '1w': 26,
    '1m': 12,
}


def decr_month(dt):
    if dt.month == 1:
        return dt.replace(month=12, year=dt.year - 1)
    return dt.replace(month=dt.month - 1)


def decr_week(dt):
    return dt - timedelta(days=7)


class ProjectStatsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('resolution', type=unicode, location='args',
                        choices=RESOLUTION_CHOICES, default='1d')
    parser.add_argument('stat', type=unicode, location='args',
                        choices=STAT_CHOICES, required=True)
    parser.add_argument('agg', type=unicode, location='args',
                        choices=AGG_CHOICES)
    parser.add_argument('points', type=int, location='args')
    parser.add_argument('from', type=int, location='args',
                        dest='from_date')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        points = args.points or POINTS_DEFAULT[args.resolution]

        if args.from_date:
            date_end = datetime.fromtimestamp(args.from_date)
        else:
            date_end = datetime.now()

        date_end = date_end.replace(
            minute=0, second=0, microsecond=0)

        if args.resolution == '1h':
            grouper = func.date_trunc('hour', Build.date_created)
            decr_res = lambda x: x - timedelta(hours=1)
        elif args.resolution == '1d':
            grouper = func.date_trunc('day', Build.date_created)
            date_end = date_end.replace(hour=0)
            decr_res = lambda x: x - timedelta(days=1)
        elif args.resolution == '1w':
            grouper = func.date_trunc('week', Build.date_created)
            date_end = date_end.replace(hour=0)
            date_end -= timedelta(days=date_end.weekday())
            decr_res = decr_week
        elif args.resolution == '1m':
            grouper = func.date_trunc('month', Build.date_created)
            date_end = date_end.replace(hour=0, day=1)
            decr_res = decr_month

        if args.agg:
            value = getattr(func, args.agg)(ItemStat.value)
        else:
            value = func.avg(ItemStat.value)

        date_begin = date_end.replace()
        for _ in xrange(points):
            date_begin = decr_res(date_begin)

        # TODO(dcramer): put minimum date bounds
        results = dict(db.session.query(
            grouper.label('grouper'),
            value.label('value'),
        ).filter(
            ItemStat.item_id == Build.id,
            ItemStat.name == args.stat,
            Build.date_created >= date_begin,
            Build.date_created < date_end,
        ).group_by('grouper'))

        data = []
        cur_date = date_end.replace()
        for _ in xrange(points):
            cur_date = decr_res(cur_date)
            data.append({
                'time': int(float(cur_date.strftime('%s.%f')) * 1000),
                'value': int(float(results.get(cur_date, 0))),
            })
        data.reverse()

        return self.respond(data, serialize=False)
