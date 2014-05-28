from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.config import db
from changes.constants import Result, Status, ProjectStatus
from changes.models import Project, Repository, Build, Source


def get_latest_builds_query(project_list, result=None):
    build_query = db.session.query(
        Build.id,
    ).join(
        Source, Build.source_id == Source.id,
    ).filter(
        Source.patch_id == None,  # NOQA
        Build.status == Status.finished,
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
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=unicode, required=True)
    parser.add_argument('slug', type=str)
    parser.add_argument('repository', type=unicode, required=True)

    def get(self):
        queryset = Project.query.filter(
            Project.status == ProjectStatus.active,
        ).order_by(Project.name.asc())

        project_list = list(queryset)

        context = []

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
            context.append(data)

        return self.paginate(context)

    @requires_auth
    def post(self):
        args = self.parser.parse_args()

        slug = str(args.slug or args.name.replace(' ', '-').lower())

        match = Project.query.filter(
            Project.slug == slug,
        ).first()
        if match:
            return '{"error": "Project with slug %r already exists"}' % (slug,), 400

        repository = Repository.get(args.repository)
        if repository is None:
            repository = Repository(
                url=args.repository,
            )
            db.session.add(repository)

        project = Project(
            name=args.name,
            slug=slug,
            repository=repository,
        )
        db.session.add(project)
        db.session.commit()

        return self.respond(project)

    def get_stream_channels(self):
        return ['builds:*']
