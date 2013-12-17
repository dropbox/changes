import itertools
import random

from hashlib import sha1
from loremipsum import get_paragraphs, get_sentences
from slugify import slugify
from uuid import uuid4

from changes.config import db
from changes.constants import Status, Result
from changes.models import (
    Project, Repository, Author, Revision, Build, BuildPhase, BuildStep,
    TestResult, TestResultManager, Change, LogChunk, TestSuite
)
from changes.db.utils import get_or_create


TEST_PACKAGES = itertools.cycle([
    'tests/changes/handlers/test_xunit.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/backends/koality/test_backend.py',
])

TEST_NAMES = itertools.cycle([
    'ListBuildsTest.test_simple',
    'SyncBuildDetailsTest.test_simple',
])

TEST_STEP_LABELS = itertools.cycle([
    'tests/changes/web/frontend/test_build_list.py',
    'tests/changes/web/frontend/test_build_details.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/handlers/test_xunit.py',
])


def repository(**kwargs):
    if 'url' not in kwargs:
        kwargs['url'] = 'https://github.com/example-{0}/example.git'.format(
            random.randint(1, 100000))

    try:
        result = Repository.query.filter_by(url=kwargs['url'])[0]
    except IndexError:
        result = Repository(**kwargs)
        db.session.add(result)
    return result


def project(repository, **kwargs):
    if 'name' not in kwargs:
        kwargs['name'] = '{0} {1}'.format(
            get_sentences(1)[0].split(' ')[0], random.randint(1, 100000))

    result = Project(repository=repository, **kwargs)
    db.session.add(result)
    return result


def author(**kwargs):
    if 'name' not in kwargs:
        kwargs['name'] = ' '.join(get_sentences(1)[0].split(' ')[0:2])
    if 'email' not in kwargs:
        kwargs['email'] = '{0}@example.com'.format(slugify(kwargs['name']))
    try:
        result = Author.query.filter_by(email=kwargs['email'])[0]
    except IndexError:
        result = Author(**kwargs)
        db.session.add(result)
    return result


def change(project, **kwargs):
    if 'message' not in kwargs:
        kwargs['message'] = '\n\n'.join(get_paragraphs(2))

    if 'label' not in kwargs:
        diff_id = 'D{0}'.format(random.randint(1000, 100000))
        kwargs['label'] = '{0}: {1}'.format(
            diff_id, kwargs['message'].splitlines()[0]
        )[:128]
    else:
        diff_id = None

    if 'hash' not in kwargs:
        kwargs['hash'] = sha1(diff_id or uuid4().hex).hexdigest()

    kwargs.setdefault('repository', project.repository)

    result = Change(project=project, **kwargs)
    db.session.add(result)
    return result


def build(change, **kwargs):
    kwargs.setdefault('label', get_sentences(1)[0])
    kwargs.setdefault('status', Status.finished)
    kwargs.setdefault('result', Result.passed)
    kwargs.setdefault('repository', change.repository)
    kwargs.setdefault('project', change.project)
    kwargs.setdefault('author', change.author)

    build = Build(change=change, **kwargs)
    db.session.add(build)

    phase1_setup = BuildPhase(
        repository=build.repository, project=build.project, build=build,
        status=Status.finished, result=Result.passed, label='Setup',
    )
    db.session.add(phase1_setup)

    phase1_compile = BuildPhase(
        repository=build.repository, project=build.project, build=build,
        status=Status.finished, result=Result.passed, label='Compile',
    )
    db.session.add(phase1_compile)

    phase1_test = BuildPhase(
        repository=build.repository, project=build.project, build=build,
        status=kwargs['status'], result=kwargs['result'], label='Test',
    )
    db.session.add(phase1_test)

    step = BuildStep(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=phase1_test.status, result=phase1_test.result,
        label=TEST_STEP_LABELS.next(),
    )
    db.session.add(step)
    step = BuildStep(
        repository=build.repository, project=build.project, build=build,
        phase=phase1_test, status=phase1_test.status, result=phase1_test.result,
        label=TEST_STEP_LABELS.next(),
    )
    db.session.add(step)

    return build


def logchunk(source, **kwargs):
    # TODO(dcramer): we should default offset to previosu entry in LogSource
    kwargs.setdefault('offset', 0)

    text = kwargs.pop('text', None) or '\n'.join(get_sentences(4))

    logchunk = LogChunk(
        source=source,
        build=source.build,
        project=source.project,
        text=text,
        size=len(text),
        **kwargs
    )
    db.session.add(logchunk)
    return logchunk


def revision(repository, author):
    result = Revision(
        repository=repository, sha=uuid4().hex, author=author,
        message='\n\n'.join(get_paragraphs(2)),
    )
    db.session.add(result)

    return result


def test_suite(build, name='default'):
    suite, _ = get_or_create(TestSuite, where={
        'build': build,
        'name': name,
    }, defaults={
        'project': build.project,
    })

    return suite


def test_result(build, **kwargs):
    if 'package' not in kwargs:
        kwargs['package'] = TEST_PACKAGES.next()

    if 'name' not in kwargs:
        kwargs['name'] = TEST_NAMES.next() + '_' + uuid4().hex

    if 'suite' not in kwargs:
        kwargs['suite'] = test_suite(build)

    if 'duration' not in kwargs:
        kwargs['duration'] = random.randint(0, 3000)

    kwargs.setdefault('result', Result.passed)

    result = TestResult(build=build, **kwargs)
    TestResultManager(build).save([result])

    return result
