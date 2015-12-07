from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict

from flask.ext.restful import reqparse
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.api.auth import requires_admin
from changes.config import db, statsreporter
from changes.constants import Cause, Result, Status, ProjectStatus
from changes.models import Project, Repository, Build, Source, Plan, PlanStatus, ProjectOption


STATUS_CHOICES = ('', 'active', 'inactive')

SORT_CHOICES = ('name', 'date')


def get_latest_builds_query(project_list, result=None):
    build_query = db.session.query(
        Build.id,
    ).join(
        Source, Build.source_id == Source.id,
    ).filter(
        Source.patch_id == None,  # NOQA
        Build.status == Status.finished,
        Build.cause != Cause.snapshot,
        # Exclude snapshot validation and commit queue builds.
        ~Build.tags.any('test-snapshot'),
        ~Build.tags.any('commit-queue'),
        Build.result.in_([Result.passed, Result.failed, Result.infra_failed]),
    ).order_by(
        Build.date_created.desc(),
    )

    if result:
        build_query = build_query.filter(
            Build.result == result,
        )

    # TODO(dcramer): we dont actually need the project table here
    build_map = dict(db.session.query(
        Project.id,
        build_query.filter(
            Build.project_id == Project.id,
        ).limit(1).as_scalar(),
    ).filter(
        Project.id.in_(p.id for p in project_list),
    ))

    return list(Build.query.filter(
        Build.id.in_(build_map.values()),
    ).options(
        joinedload('author'),
        joinedload('source').joinedload('revision'),
    ))


class ProjectIndexAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('status', type=unicode, location='args',
                            choices=STATUS_CHOICES, default='active')
    get_parser.add_argument('sort', type=unicode, location='args',
                            choices=SORT_CHOICES, default='name')
    # grabs extra data to show a richer ui in the new changes ui
    get_parser.add_argument('fetch_extra', type=unicode, location='args', default=0)

    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name', type=unicode, required=True)
    post_parser.add_argument('slug', type=str)
    post_parser.add_argument('repository', type=unicode, required=True)

    def get(self):
        args = self.get_parser.parse_args()

        # This project index generation is a prerequisite for rendering
        # the homepage and the admin page; worth tracking both for user
        # experience and to keep an eye on database responsiveness.
        with statsreporter.stats().timer('generate_project_index'):
            queryset = Project.query

            if args.query:
                queryset = queryset.filter(
                    or_(
                        func.lower(Project.name).contains(args.query.lower()),
                        func.lower(Project.slug).contains(args.query.lower()),
                    ),
                )

            if args.status:
                queryset = queryset.filter(
                    Project.status == ProjectStatus[args.status]
                )

            if args.sort == 'name':
                queryset = queryset.order_by(Project.name.asc())
            elif args.sort == 'date':
                queryset = queryset.order_by(Project.date_created.asc())

            plans = []
            if args.fetch_extra:
                queryset = queryset.options(
                    joinedload(Project.repository, innerjoin=True)
                )

                # fetch plans separately to avoid many lazy database fetches
                plans_list = self.serialize(list(Plan.query.filter(
                    Plan.status == PlanStatus.active
                ).options(
                    joinedload(Plan.steps)
                )))

                plans = defaultdict(list)
                for p in plans_list:
                    plans[p['project_id']].append(p)

                # we could use the option names whitelist from
                # project_details.py
                options_list = list(ProjectOption.query)
                options_dict = defaultdict(dict)

                for o in options_list:
                    options_dict[o.project_id][o.name] = o.value

            project_list = list(queryset)

            context = []
            if project_list:
                latest_build_results = get_latest_builds_query(project_list)
                latest_build_map = dict(
                    zip([b.project_id for b in latest_build_results],
                        self.serialize(latest_build_results))
                )

                passing_build_map = {}
                missing_passing_builds = set()
                for build in latest_build_results:
                    if build.result == Result.passed:
                        passing_build_map[build.project_id] = build
                    else:
                        passing_build_map[build.project_id] = None
                        missing_passing_builds.add(build.project_id)

                if missing_passing_builds:
                    passing_build_results = get_latest_builds_query(
                        project_list, result=Result.passed,
                    )
                    passing_build_map.update(dict(
                        zip([b.project_id for b in passing_build_results],
                            self.serialize(passing_build_results))
                    ))

                for project, data in zip(project_list, self.serialize(project_list)):
                    # TODO(dcramer): build serializer is O(N) for stats
                    data['lastBuild'] = latest_build_map.get(project.id)
                    data['lastPassingBuild'] = passing_build_map.get(project.id)
                    if args.fetch_extra:
                        data['repository'] = self.serialize(project.repository)
                        data['options'] = options_dict[project.id]
                        # we have to use the serialized version of the id
                        data['plans'] = plans[data['id']]
                    context.append(data)

            return self.respond(context)

    @requires_admin
    def post(self):
        args = self.post_parser.parse_args()

        slug = str(args.slug or args.name.replace(' ', '-').lower())

        match = Project.query.filter(
            Project.slug == slug,
        ).first()
        if match:
            return '{"error": "Project with slug %r already exists"}' % (slug,), 400

        repository = Repository.get(args.repository)
        if repository is None:
            return '{"error": "Repository with url %r does not exist"}' % (args.repository,), 400

        project = Project(
            name=args.name,
            slug=slug,
            repository=repository,
        )
        db.session.add(project)
        db.session.commit()

        return self.respond(project)
