from datetime import datetime

from changes.config import db
from changes.constants import Result
from changes.models.log import LogSource, LogChunk
from changes.lib import build_context_lib
from changes.testutils.cases import TestCase


class GetTitleTestCase(TestCase):
    def test_get_title(self):
        self.assertEqual(
            'D123 passed - My \u00fcnicode diff',
            build_context_lib._get_title('D123', 'My \u00fcnicode diff', Result.passed),
        )

        self.assertEqual(
            'Build passed - My \u00fcnicode diff',
            build_context_lib._get_title(None, 'My \u00fcnicode diff', Result.passed),
        )

        self.assertEqual(
            'Build passed - My \u00fcnicode diff...',
            build_context_lib._get_title(
                None, 'My \u00fcnicode diff\nwith many lines', Result.passed),
        )


class BuildingContextTestCase(TestCase):
    def test_simple(self):
        project = self.create_project(name='test', slug='test')

        def test_with_result(result):
            revision_id = 'revision_id'
            revision_url = 'revision_url'
            source = self.create_source(project, data={
                'phabricator.revisionID': revision_id,
                'phabricator.revisionURL': revision_url
            })
            build = self.create_build(
                project,
                label='Test diff',
                date_started=datetime.utcnow(),
                result=result,
                source=source
            )
            job = self.create_job(build=build, result=Result.failed)
            phase = self.create_jobphase(job=job)
            step = self.create_jobstep(phase=phase)
            logsource = self.create_logsource(
                step=step,
                name='console',
            )
            self.create_logchunk(
                source=logsource,
                text='hello world',
            )

            context = build_context_lib.get_collection_context([build])
            if result is not Result.passed and result is not Result.failed:
                result = Result.unknown

            assert context['title'] == '%s %s - %s' % (
                'D{}'.format(revision_id), str(result).lower(), job.build.label)
            assert len(context['builds']) == 1
            assert context['result'] == result
            assert context['target_uri'] == revision_url
            assert context['target'] == 'D{}'.format(revision_id)
            assert context['label'] == build.label
            assert context['date_created'] == build.date_created
            assert context['author'] == build.author
            assert context['commit_message'] == ''
            assert context['failing_tests_count'] == 0

        test_with_result(Result.passed)
        test_with_result(Result.skipped)
        test_with_result(Result.unknown)
        test_with_result(Result.aborted)
        test_with_result(Result.infra_failed)
        test_with_result(Result.failed)

    def test_multiple_builds(self):
        project = self.create_project(name='test', slug='test')
        revision_id = 'revision_id'
        revision_url = 'revision_url'
        source = self.create_source(project, data={
            'phabricator.revisionID': revision_id,
            'phabricator.revisionURL': revision_url
        })

        def create_build(result):
            build = self.create_build(
                project,
                label='test diff',
                date_started=datetime.utcnow(),
                result=result,
                source=source
            )
            job = self.create_job(build=build, result=Result.failed)
            phase = self.create_jobphase(job=job)
            step = self.create_jobstep(phase=phase)
            logsource = self.create_logsource(
                step=step,
                name='console',
            )
            self.create_logchunk(
                source=logsource,
                text='hello world',
            )
            return build
        build1 = create_build(Result.failed)
        build2 = create_build(Result.infra_failed)
        build3 = create_build(Result.aborted)
        build4 = create_build(Result.unknown)
        build5 = create_build(Result.skipped)
        build6 = create_build(Result.passed)
        builds_wrong_order = [build2, build3, build1, build4, build6, build5]
        builds_correct_order = [build1, build2, build3, build4, build5, build6]

        context = build_context_lib.get_collection_context(builds_wrong_order)

        first_build = builds_correct_order[0]

        assert context['title'] == '%s failed - %s' % (
            'D{}'.format(revision_id), first_build.label)
        for i in range(len(context['builds'])):
            assert context['builds'][i]['build'] == builds_correct_order[i]
        assert context['result'] == Result.failed
        assert context['target_uri'] == revision_url
        assert context['target'] == 'D{}'.format(revision_id)
        assert context['label'] == first_build.label
        assert context['date_created'] == build1.date_created
        assert context['author'] == first_build.author
        assert context['commit_message'] == ''
        assert context['failing_tests_count'] == 0


class GetLogClippingTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        logsource = LogSource(
            project=project,
            job=job,
            name='console',
        )
        db.session.add(logsource)

        logchunk = LogChunk(
            project=project,
            job=job,
            source=logsource,
            offset=0,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        logchunk = LogChunk(
            project=project,
            job=job,
            source=logsource,
            offset=11,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        db.session.commit()

        result = build_context_lib._get_log_clipping(logsource, max_size=200, max_lines=3)
        assert result == "world\r\nhello\r\nworld"

        result = build_context_lib._get_log_clipping(logsource, max_size=200, max_lines=1)
        assert result == "world"

        result = build_context_lib._get_log_clipping(logsource, max_size=5, max_lines=3)
        assert result == "world"

    def test_no_log_chunks(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        logsource = LogSource(
            project=project,
            job=job,
            name='console',
        )
        db.session.add(logsource)
        db.session.commit()

        result = build_context_lib._get_log_clipping(logsource)
        assert result == ""
