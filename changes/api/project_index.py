from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict

from flask.ext.restful import reqparse
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.api.auth import requires_admin
from changes.config import db, statsreporter
from changes.constants import Result, Status, ProjectStatus
from changes.lib import build_type
from changes.models.project import Project, ProjectOption
from changes.models.repository import Repository
from changes.models.build import Build
from changes.models.source import Source
from changes.models.plan import Plan, PlanStatus


STATUS_CHOICES = ('', 'active', 'inactive')

SORT_CHOICES = ('name', 'date')


def get_latest_builds_query(project_ids, result=None):
    build_query = db.session.query(
        Build.id,
    ).join(
        Source, Build.source_id == Source.id,
    ).filter(
        Build.status == Status.finished,
        Build.result.in_([Result.passed, Result.failed, Result.infra_failed]),
        *build_type.get_any_commit_build_filters()
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
        Project.id.in_(project_ids),
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
                latest_build_results = get_latest_builds_query(p.id for p in project_list)

                projects_missing_passing_build = []
                for build in latest_build_results:
                    if build.result != Result.passed:
                        projects_missing_passing_build.append(build.project_id)

                if projects_missing_passing_build:
                    extra_passing_build_results = get_latest_builds_query(
                        projects_missing_passing_build, result=Result.passed,
                    )
                else:
                    extra_passing_build_results = []

                # serialize as a group for more effective batching
                serialized_builds = self.serialize(latest_build_results + extra_passing_build_results)

                serialized_latest_builds = serialized_builds[:len(latest_build_results)]
                serialized_extra_passing_builds = serialized_builds[-len(extra_passing_build_results):]
                latest_build_map = dict(
                    zip([b.project_id for b in latest_build_results],
                        serialized_latest_builds)
                )
                passing_build_map = {}
                for build in latest_build_results:
                    if build.result == Result.passed:
                        passing_build_map[build.project_id] = latest_build_map.get(build.project_id)
                    else:
                        passing_build_map[build.project_id] = None
                passing_build_map.update(
                    zip([b.project_id for b in extra_passing_build_results],
                        serialized_extra_passing_builds)
                )

                if args.fetch_extra:
                    repo_ids = set()
                    repos = []
                    for project in project_list:
                        if project.repository_id not in repo_ids:
                            repos.append(project.repository)
                            repo_ids.add(project.repository)
                    repo_dict = dict(
                        zip([repo.id for repo in repos],
                            self.serialize(repos))
                    )
                for project, data in zip(project_list, self.serialize(project_list)):
                    data['lastBuild'] = latest_build_map.get(project.id)
                    data['lastPassingBuild'] = passing_build_map.get(project.id)
                    if args.fetch_extra:
                        data['repository'] = repo_dict[project.repository_id]
                        data['options'] = options_dict[project.id]
                        # we have to use the serialized version of the id
                        data['plans'] = plans[data['id']]
                    context.append(data)

            return self.respond(context, serialize=False)

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
