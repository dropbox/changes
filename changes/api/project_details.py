from __future__ import division

from datetime import datetime, timedelta
from flask.ext.restful import reqparse
from sqlalchemy.orm import contains_eager, joinedload
from sqlalchemy.sql import func

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.lib import build_type
from changes.models.build import Build
from changes.models.project import Project, ProjectOption, ProjectStatus
from changes.models.repository import Repository
from changes.models.source import Source


OPTION_DEFAULTS = {
    'green-build.notify': '0',
    'green-build.project': '',
    'mail.notify-author': '1',
    'mail.notify-addresses': '',
    'mail.notify-addresses-revisions': '',
    'build.commit-trigger': '1',
    'build.file-whitelist': '',
    'phabricator.diff-trigger': '1',
    'ui.show-coverage': '1',
    'ui.show-tests': '1',
    'snapshot.current': '',
}

STATUS_CHOICES = ('active', 'inactive')


class ProjectDetailsAPIView(APIView):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name')
    post_parser.add_argument('slug')
    post_parser.add_argument('repository')
    post_parser.add_argument('status', choices=STATUS_CHOICES)

    def _get_avg_duration(self, project, start_period, end_period):
        avg_duration = db.session.query(
            func.avg(Build.duration)
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Build.project_id == project.id,
            Build.date_created >= start_period,
            Build.date_created < end_period,
            Build.status == Status.finished,
            Build.result == Result.passed,
            *build_type.get_any_commit_build_filters()
        ).scalar() or None
        if avg_duration is not None:
            avg_duration = float(avg_duration)
        return avg_duration

    def _get_green_percent(self, project, start_period, end_period):
        build_counts = dict(db.session.query(
            Build.result, func.count()
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Build.project_id == project.id,
            Build.date_created >= start_period,
            Build.date_created < end_period,
            Build.status == Status.finished,
            Build.result.in_([Result.passed, Result.failed]),
            *build_type.get_any_commit_build_filters()
        ).group_by(
            Build.result,
        ))

        failed_builds = build_counts.get(Result.failed) or 0
        passed_builds = build_counts.get(Result.passed) or 0
        if passed_builds:
            green_percent = int((passed_builds / (failed_builds + passed_builds)) * 100)
        elif failed_builds:
            green_percent = 0
        else:
            green_percent = None

        return green_percent

    def _get_stats(self, project):
        window = timedelta(days=7)

        end_period = datetime.utcnow()
        start_period = end_period - window

        prev_end_period = start_period
        prev_start_period = start_period - window

        green_percent = self._get_green_percent(project, start_period, end_period)
        prev_green_percent = self._get_green_percent(
            project, prev_start_period, prev_end_period)

        avg_duration = self._get_avg_duration(project, start_period, end_period)
        prev_avg_duration = self._get_avg_duration(
            project, prev_start_period, prev_end_period)

        return {
            'greenPercent': green_percent,
            'previousGreenPercent': prev_green_percent,
            'avgDuration': avg_duration,
            'previousAvgDuration': prev_avg_duration,
        }

    def get(self, project_id):
        project = Project.get(project_id)
        if project is None:
            return '', 404

        last_build = Build.query.options(
            joinedload('author'),
            contains_eager('source')
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Build.project == project,
            Build.status == Status.finished,
            *build_type.get_any_commit_build_filters()
        ).order_by(
            Build.date_created.desc(),
        ).first()
        if not last_build or last_build.result == Result.passed:
            last_passing_build = last_build
        else:
            last_passing_build = Build.query.options(
                joinedload('author'),
                contains_eager('source')
            ).join(
                Source, Build.source_id == Source.id,
            ).filter(
                Build.project == project,
                Build.result == Result.passed,
                Build.status == Status.finished,
                *build_type.get_any_commit_build_filters()
            ).order_by(
                Build.date_created.desc(),
            ).first()

        options = dict(
            (o.name, o.value) for o in ProjectOption.query.filter(
                ProjectOption.project_id == project.id,
            )
        )
        for key, value in OPTION_DEFAULTS.iteritems():
            options.setdefault(key, value)

        data = self.serialize(project)
        data['lastBuild'] = last_build
        data['lastPassingBuild'] = last_passing_build
        data['repository'] = project.repository
        data['options'] = options
        data['stats'] = self._get_stats(project)

        return self.respond(data)

    @requires_admin
    def post(self, project_id):
        project = Project.get(project_id)
        if project is None:
            return '', 404

        args = self.post_parser.parse_args()

        if args.name:
            project.name = args.name

        if args.slug:
            match = Project.query.filter(
                Project.slug == args.slug,
                Project.id != project.id,
            ).first()
            if match:
                return '{"error": "Project with slug %r already exists"}' % (args.slug,), 400

            project.slug = args.slug

        if args.repository:
            repository = Repository.get(args.repository)
            if repository is None:
                return '{"error": "Repository with url %r does not exist"}' % (args.repository,), 400
            project.repository = repository

        if args.status == 'inactive':
            project.status = ProjectStatus.inactive
        elif args.status == 'active':
            project.status = ProjectStatus.active

        db.session.add(project)

        data = self.serialize(project)
        data['repository'] = self.serialize(project.repository)

        return self.respond(data, serialize=False)
