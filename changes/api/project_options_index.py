from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.db.utils import create_or_update
from changes.models import Project, ProjectOption


class ProjectOptionsIndexAPIView(APIView):
    # TODO(dcramer): these shouldn't be static
    parser = reqparse.RequestParser()
    parser.add_argument('green-build.notify')
    parser.add_argument('green-build.project')
    parser.add_argument('mail.notify-author')
    parser.add_argument('mail.notify-addresses')
    parser.add_argument('mail.notify-addresses-revisions')
    parser.add_argument('build.allow-patches')
    parser.add_argument('build.branch-names')
    parser.add_argument('build.commit-trigger')
    parser.add_argument('build.test-duration-warning')
    parser.add_argument('hipchat.notify')
    parser.add_argument('hipchat.room')
    parser.add_argument('ui.show-coverage')
    parser.add_argument('ui.show-tests')

    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository, innerjoin=True),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository, innerjoin=True),
            ).get(project_id)
        return project

    @requires_auth
    def post(self, project_id):
        project = self._get_project(project_id)
        if project is None:
            return '', 404

        args = self.parser.parse_args()

        for name, value in args.iteritems():
            if value is None:
                continue
            create_or_update(ProjectOption, where={
                'project': project,
                'name': name,
            }, values={
                'value': value,
            })

        return '', 200
