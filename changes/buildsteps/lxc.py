from __future__ import absolute_import

from flask import current_app
from uuid import uuid4

from changes.buildsteps.default import DefaultBuildStep
from changes.config import db
from changes.models import (
    CommandType, FutureCommand, JobPlan, Snapshot, SnapshotImage
)
from changes.utils.http import build_uri


WRITE_TO_FILE_COMMAND = """
#!/bin/bash -eux

{ cat <<"EOF"
%(script)s
EOF
} | tee %(filename)s
""".strip()


class LXCBuildStep(DefaultBuildStep):
    """
    Similar to the default build step, except that things are run within
    an LXC container.
    """
    changes_lxc_bin = 'changes-lxc'

    def get_label(self):
        return 'Build via Changes Client (LXC)'

    def get_snapshot_image(self, job):
        # determine if there's an expected snapshot outcome
        expected_image = SnapshotImage.query.filter(
            SnapshotImage.job_id == job.id,
        ).first()

        # we only send a current snapshot if we're not expecting to build
        # a new image
        if expected_image:
            return None

        jobplan = JobPlan.query.filter(
            JobPlan.job_id == job.id,
        ).first()

        current_snapshot = Snapshot.get_current(job.project_id)
        if current_snapshot and jobplan:
            image = db.session.query(
                SnapshotImage.id,
            ).filter(
                SnapshotImage.snapshot_id == current_snapshot.id,
                SnapshotImage.plan_id == jobplan.plan_id,
            ).scalar()
            return str(image) if image else None

        elif current_app.config['DEFAULT_SNAPSHOT']:
            return current_app.config['DEFAULT_SNAPSHOT']

        return None

    def iter_all_commands(self, job):
        current_image = self.get_snapshot_image(job)
        container_name = uuid4().hex

        launch_cmd = '#!/bin/bash -eux\n{bin} launch {container} ' \
            '--release={release} ' \
            '--s3-bucket={s3_bucket} ' \
            '--pre-launch="{pre_launch}" ' \
            '--post-launch="{post_launch}"'.format(
                bin=self.changes_lxc_bin,
                container=container_name,
                release=self.release,
                s3_bucket=current_app.config['SNAPSHOT_S3_BUCKET'],
                pre_launch=current_app.config['LXC_PRE_LAUNCH'],
                post_launch=current_app.config['LXC_POST_LAUNCH'],
            )
        if current_image:
            launch_cmd = '{} --snapshot={}'.format(launch_cmd, current_image)

        yield FutureCommand(
            script=launch_cmd,
            type=CommandType.setup,
        )

        for command in self.iter_vcs_commands(job, container_name):
            yield command

        exec_cmd = '#!/bin/bash -eux\n{bin} exec {container} -- '.format(
            bin=self.changes_lxc_bin,
            container=container_name,
        )

        for command in self.commands:
            command = command.copy()
            command['script'] = exec_cmd + command['script']
            yield FutureCommand(**command)

        yield FutureCommand(
            script='#!/bin/bash -eux\n{bin} destroy {container}'.format(
                bin=self.changes_lxc_bin,
                container=container_name,
            ),
            type=CommandType.teardown,
        )

    def iter_vcs_commands(self, job, container_name):
        source = job.source
        repo = source.repository
        vcs = repo.get_vcs()
        if vcs is not None:
            exec_script_cmd = '#!/bin/bash -eux\n{bin} exec-script {container} '.format(
                bin=self.changes_lxc_bin,
                container=container_name,
            )

            yield FutureCommand(
                script=self.write_to_file_command(
                    '/tmp/update-source', vcs.get_buildstep_clone(source, self.path)
                ),
                env=self.env,
                type=CommandType.setup,
            )
            yield FutureCommand(
                script=exec_script_cmd + '/tmp/update-source',
                env=self.env,
                type=CommandType.setup,
            )

            if source.patch:
                yield FutureCommand(
                    script=self.write_to_file_command(
                        '/tmp/apply-patch', vcs.get_buildstep_patch(source, self.path)
                    ),
                    env=self.env,
                )
                yield FutureCommand(
                    script=exec_script_cmd + '/tmp/apply-patch',
                    env=self.env,
                )

    def write_to_file_command(self, filename, script):
        return WRITE_TO_FILE_COMMAND % dict(
            filename=filename,
            script=script,
        )

    def get_allocation_command(self, jobstep):
        args = {
            'api_url': build_uri('/api/0/'),
            'jobstep_id': jobstep.id.hex,
        }
        return "changes-client " \
            "--server %(api_url)s " \
            "--jobstep_id %(jobstep_id)s" % args
