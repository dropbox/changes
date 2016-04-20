from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView, error
from changes.config import db
from changes.models.build import Build
from changes.models.job import Job
from changes.models.phabricatordiff import PhabricatorDiff

from changes.utils.phabricator_utils import PhabricatorClient


class DiffBuildsIndexAPIView(APIView):

    """
    For a given diff_id, returns the list of builds associated with that diff.

    diff_ident: is the D12342 number, including the D (naming note: other parts
    of the code use revision_id for that number and diff_id for each individual
    code diff within a differential diff
    """

    def get(self, diff_ident):
        if not diff_ident.startswith('D') or not diff_ident[1:].isdigit():
            return error('diff id not valid')

        # grab diff info from phabricator.
        phabricator_info = {}
        try:
            request = PhabricatorClient()
            request.connect()

            phabricator_info = request.call('differential.query', {
                'ids': [int(diff_ident[1:])]
            })
            if len(phabricator_info) == 0:
                return error('%s not found in phabricator' % diff_ident, http_code=404)
            assert len(phabricator_info) == 1
            phabricator_info = phabricator_info[0]
            phabricator_info["fetched_data_from_phabricator"] = True
        except Exception as e:
            # If the phabricator call fails for whatever reason, we'll still
            # return the builds info from changes. We don't want changes to
            # be unusable if phabricator is down
            print e
            phabricator_info = {
                "fetched_data_from_phabricator": False
            }
            pass

        # TODO: if we want the name/email of the author of the diff, we'd have
        # to make another conduit call. Instead, we'll let the frontend rely
        # on the fact that any phabricator-tagged build always has the same
        # author as the diff

        # grab builds
        rows = list(db.session.query(
            Build, PhabricatorDiff
        ).join(
            PhabricatorDiff, Build.source_id == PhabricatorDiff.source_id,
        ).filter(
            PhabricatorDiff.revision_id == diff_ident[1:]
        ))

        build_ids = set([row.Build.id for row in rows])

        jobs = []
        if len(build_ids) > 0:
            jobs = self.serialize(list(Job.query.filter(
                Job.build_id.in_(build_ids)
            )))

        serialized_builds = zip(
            self.serialize([row.Build for row in rows]),
            [row.PhabricatorDiff for row in rows]
        )

        build_info = {}
        for build, phabricator_diff in serialized_builds:
            # we may have multiple diffs within a single differential revision
            single_diff_id = phabricator_diff.diff_id
            if single_diff_id not in build_info:
                build_info[single_diff_id] = {
                    'id': phabricator_diff.id,
                    'builds': [],
                    'diff_id': phabricator_diff.diff_id,
                    'revision_id': phabricator_diff.revision_id,
                    'url': phabricator_diff.url,
                    'source_id': phabricator_diff.source_id,
                    'dateCreated': phabricator_diff.date_created
                }
            build['jobs'] = [j for j in jobs if j['build']['id'] == build['id']]
            build_info[single_diff_id]['builds'].append(build)

        phabricator_info['changes'] = build_info

        return self.respond(phabricator_info)
