from __future__ import absolute_import

from mock import patch
from uuid import UUID

from changes.buildsteps.lxc import LXCBuildStep
from changes.constants import Status
from changes.models import Command, CommandType
from changes.testutils import BackendTestCase


class LXCBuildStepTest(BackendTestCase):
    def setUp(self):
        self.project = self.create_project()
        super(LXCBuildStepTest, self).setUp()

    def get_buildstep(self):
        return LXCBuildStep(commands=(
            dict(
                script='echo "hello world 2"',
                type='setup',
            ),
            dict(
                script='echo "hello world 1"',
            ),
        ), release='precise')

    @patch('changes.buildsteps.lxc.uuid4')
    def test_execute(self, mock_uuid4):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        mock_uuid4.return_value = UUID('2f142451-6eca-469d-a908-e1438b991470')

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        step = job.phases[0].steps[0]

        assert step.status == Status.pending_allocation

        commands = list(Command.query.filter(
            Command.jobstep_id == step.id,
        ))
        assert len(commands) == 4

        assert commands[0].script == '#!/bin/bash -eux\nchanges-lxc launch 2f1424516eca469da908e1438b991470 --release=precise'
        assert commands[0].type == CommandType.setup

        assert commands[1].script == '#!/bin/bash -eux\nchanges-lxc exec 2f1424516eca469da908e1438b991470 -- echo "hello world 2"'
        assert commands[1].type == CommandType.setup

        assert commands[2].script == '#!/bin/bash -eux\nchanges-lxc exec 2f1424516eca469da908e1438b991470 -- echo "hello world 1"'
        assert commands[2].type == CommandType.default

        assert commands[3].script == '#!/bin/bash -eux\nchanges-lxc destroy 2f1424516eca469da908e1438b991470'
        assert commands[3].type == CommandType.teardown

    def test_write_to_file_command(self):
        buildstep = self.get_buildstep()
        result = buildstep.write_to_file_command('/tmp/foo.sh', '#!/bin/bash -eux\necho 1')

        assert result == """#!/bin/bash -eux

{ cat <<"EOF"
#!/bin/bash -eux
echo 1
EOF
} | tee /tmp/foo.sh"""
