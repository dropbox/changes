from __future__ import absolute_import

from flask import current_app

from changes.buildsteps.default import DefaultBuildStep
from changes.config import db
from changes.models import SnapshotImage
from changes.utils.http import build_uri


class LXCBuildStep(DefaultBuildStep):
    """
    Similar to the default build step, except that it runs the client using
    the LXC adapter.
    """
    def get_label(self):
        return 'Build via Changes Client (LXC)'

    def get_allocation_command(self, jobstep):
        args = {
            'api_url': build_uri('/api/0/'),
            'jobstep_id': jobstep.id.hex,
            's3_bucket': current_app.config['SNAPSHOT_S3_BUCKET'],
            'pre_launch': current_app.config['LXC_PRE_LAUNCH'],
            'post_launch': current_app.config['LXC_POST_LAUNCH'],
            'release': self.release,
        }
        command = "changes-client " \
            "-adapter lxc " \
            "-server %(api_url)s " \
            "-jobstep_id %(jobstep_id)s " \
            "-release %(release)s " \
            "-s3-bucket %(s3_bucket)s " \
            "-pre-launch \"%(pre_launch)s\" " \
            "-post-launch \"%(post_launch)s\"" % args

        # TODO(dcramer): we need some kind of tie into the JobPlan in order
        # to dictate that this is a snapshot build
        # determine if there's an expected snapshot outcome
        expected_image = db.session.query(
            SnapshotImage.id,
        ).filter(
            SnapshotImage.job_id == jobstep.job_id,
        ).scalar()
        if expected_image:
            command = "%s -save-snapshot %s" % (command, expected_image.hex)

        return command
