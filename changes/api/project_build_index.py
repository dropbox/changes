from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from sqlalchemy import or_
from sqlalchemy.orm import contains_eager, joinedload

from changes.api.auth import get_current_user
from changes.api.base import APIView
from changes.constants import Cause, Result
from changes.models import Author, Project, Source, Build

from changes.utils.phabricator_utils import (might_be_diffusion_iden,
                                             get_hash_from_diffusion_iden)


def validate_author(author_id):
    current_user = get_current_user()
    if author_id == 'me' and not current_user:
        raise ValueError('You are not signed in.')

    return Author.find(author_id, current_user)


class ProjectBuildIndexAPIView(APIView):
    get_parser = RequestParser()
    get_parser.add_argument('include_patches', type=lambda x: bool(int(x)), location='args',
                            default=True)
    get_parser.add_argument('author', type=validate_author, location='args',
                            dest='authors')
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('source', type=unicode, location='args')
    get_parser.add_argument('result', type=unicode, location='args',
                            choices=('failed', 'passed', 'aborted', 'unknown', ''))
    get_parser.add_argument('patches_only', type=lambda x: bool(int(x)), location='args',
                            default=False)
    get_parser.add_argument('cause', type=unicode, location='args',
                            choices=('unknown', 'manual', 'push', 'retry', 'snapshot', ''))
    get_parser.add_argument('tag', type=unicode, default='')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.get_parser.parse_args()

        filters = []

        if args.authors:
            filters.append(Build.author_id.in_([a.id for a in args.authors]))
        elif args.authors is not None:
            return []

        if args.source:
            filters.append(Build.target.startswith(args.source))

        # is this from the search bar
        if args.query:
            clauses = []
            # search by revision title
            clauses.append(Build.label.contains(args.query))
            # search by prefix
            clauses.append(Build.target.startswith(args.query))
            # allows users to paste a full commit hash and still
            # find the relevant build(s). Should be fine for mercurial/git,
            # and svn will never have long enough strings
            if len(args.query) > 12:
                clauses.append(Build.target.startswith(args.query[0:12]))
            # if they searched for something that looks like a phabricator
            # identifier, try to find it
            if might_be_diffusion_iden(args.query):
                possible_hash = get_hash_from_diffusion_iden(args.query)
                if possible_hash:
                    # the query should always be at least as long or longer than
                    # our commit identifiers
                    clauses.append(
                        Build.target.startswith(possible_hash[0:12]))
            filters.append(or_(*clauses))

        if args.result:
            filters.append(Build.result == Result[args.result])

        if args.cause:
            filters.append(Build.cause == Cause[args.cause])

        if args.tag:
            filters.append(Build.tags.any(args.tag))

        if args.patches_only:
            filters.append(Source.patch_id != None)  # NOQA
        elif not args.include_patches:
            filters.append(Source.patch_id == None)  # NOQA

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            contains_eager('source').joinedload('revision'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Build.project_id == project.id,
            *filters
        ).order_by(Build.date_created.desc())

        return self.paginate(queryset)
