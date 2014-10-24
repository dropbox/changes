from __future__ import absolute_import, division, unicode_literals

import logging

from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import subqueryload_all
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView, error
from changes.api.build_index import (
    create_build, get_build_plans, identify_revision, MissingRevision
)
from changes.api.validators.author import AuthorValidator
from changes.config import db
from changes.models import (
    ItemOption, Patch, Project, ProjectOption, ProjectStatus,
    Repository, RepositoryStatus
)


def get_repository_by_callsign(callsign):
    # It's possible to have multiple repositories with the same callsign due
    # to us not enforcing a unique constraint (via options). Given that it is
    # complex and shouldn't actually happen we make an assumption that there's
    # only a single repo
    item_id_list = db.session.query(ItemOption.item_id).filter(
        ItemOption.name == 'phabricator.callsign',
        ItemOption.value == callsign,
    )
    repo_list = list(Repository.query.filter(
        Repository.id.in_(item_id_list),
        Repository.status == RepositoryStatus.active,
    ))
    if len(repo_list) > 1:
        logging.warning('Multiple repositories found matching phabricator.callsign=%s', callsign)
    elif not repo_list:
        return None  # Match behavior of project and repository parameters
    return repo_list[0]


class PhabricatorNotifyDiffAPIView(APIView):
    parser = RequestParser()
    parser.add_argument('sha', type=str, required=True)
    parser.add_argument('author', type=AuthorValidator(), required=True)
    parser.add_argument('label', type=unicode, required=True)
    parser.add_argument('message', type=unicode, required=True)
    parser.add_argument('patch', type=FileStorage, dest='patch_file',
                        location='files', required=True)

    parser.add_argument('phabricator.callsign', type=get_repository_by_callsign,
                        required=True, dest='repository')
    parser.add_argument('phabricator.buildTargetPHID', required=False)
    parser.add_argument('phabricator.diffID', required=True)
    parser.add_argument('phabricator.revisionID', required=True)
    parser.add_argument('phabricator.revisionURL', required=True)

    def post(self):
        """
        Notify Changes of a newly created diff.

        Depending on system configuration, this may create 0 or more new builds,
        and the resulting response will be a list of those build objects.
        """
        args = self.parser.parse_args()

        repository = args.repository
        if not args.repository:
            return error("Repository not found")

        projects = list(Project.query.options(
            subqueryload_all('plans'),
        ).filter(
            Project.status == ProjectStatus.active,
            Project.repository_id == repository.id,
        ))

        # no projects bound to repository
        if not projects:
            return self.respond([])

        options = dict(
            db.session.query(
                ProjectOption.project_id, ProjectOption.value
            ).filter(
                ProjectOption.project_id.in_([p.id for p in projects]),
                ProjectOption.name.in_([
                    'phabricator.diff-trigger',
                ])
            )
        )

        projects = [
            p for p in projects
            if options.get(p.id, '1') == '1'
        ]

        if not projects:
            return self.respond([])

        label = args.label[:128]
        author = args.author
        message = args.message
        sha = args.sha
        target = 'D{}'.format(args['phabricator.revisionID'])

        try:
            identify_revision(repository, sha)
        except MissingRevision:
            return error("Unable to find commit %s in %s." % (
                sha, repository.url), problems=['sha', 'repository'])

        patch = Patch(
            repository=repository,
            parent_revision_sha=sha,
            diff=''.join(args.patch_file),
        )
        db.session.add(patch)

        patch_data = {
            'phabricator.buildTargetPHID': args['phabricator.buildTargetPHID'],
            'phabricator.diffID': args['phabricator.diffID'],
            'phabricator.revisionID': args['phabricator.revisionID'],
            'phabricator.revisionURL': args['phabricator.revisionURL'],
        }

        builds = []
        for project in projects:
            plan_list = get_build_plans(project)
            if not plan_list:
                logging.warning('No plans defined for project %s', project.slug)
                continue

            builds.append(create_build(
                project=project,
                sha=sha,
                target=target,
                label=label,
                message=message,
                author=author,
                patch=patch,
                source_data=patch_data,
            ))

        return self.respond(builds)
