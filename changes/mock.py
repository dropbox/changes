# TODO(dcramer): make the API queryable internally so we dont have to have
# multiple abstractions to creating objects
import itertools
import random

from hashlib import sha1
from loremipsum import get_paragraphs, get_sentences
from uuid import uuid4

from changes.config import db
from changes.constants import Status, Result
from changes.db.utils import get_or_create
from changes.models import (
    Project, Repository, Author, Revision, Job, JobPhase, JobStep, Node,
    TestResult, Change, LogChunk, Build, JobPlan, Plan, Source, FailureReason,
    Patch, FileCoverage, Event, EventType, Cluster, ClusterNode, Command
)
from changes.testutils.fixtures import SAMPLE_DIFF
from changes.utils.slugs import slugify


TEST_PACKAGES = [
    'tests/changes/handlers/test_xunit.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/backends/koality/test_backend.py',
]

TEST_NAMES = [
    'ListBuildsTest.test_simple',
    'SyncBuildDetailsTest.test_simple',
    'ListBuildsTest.test_complex',
    'SyncBuildDetailsTest.test_complex',
    'ListBuildsTest.test_functional',
    'SyncBuildDetailsTest.test_functional',
    'ListBuildsTest.test_nothing',
    'SyncBuildDetailsTest.test_nothing',
]

TEST_FULL_NAMES = []
for package in TEST_PACKAGES:
    for name in TEST_NAMES:
        TEST_FULL_NAMES.append('{0}::{1}'.format(package, name))
TEST_FULL_NAMES = itertools.cycle(TEST_FULL_NAMES)

TEST_STEP_LABELS = itertools.cycle([
    'tests/changes/web/frontend/test_build_list.py',
    'tests/changes/web/frontend/test_build_details.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/handlers/test_xunit.py',
])

PROJECT_NAMES = itertools.cycle([
    'Earth',
    'Wind',
    'Fire',
    'Water',
    'Heart',
])

PLAN_NAMES = itertools.cycle([
    'Build Foo',
    'Build Bar',
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
        kwargs['name'] = PROJECT_NAMES.next()

    project = Project.query.filter(
        Project.name == kwargs['name'],
    ).first()
    if project:
        return project

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
        diff_id = 'D{0}'.format(random.randint(1000, 1000000000000))
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


def build(project, **kwargs):
    kwargs.setdefault('collection_id', uuid4().hex)
    kwargs.setdefault('label', get_sentences(1)[0][:128])
    kwargs.setdefault('status', Status.finished)
    kwargs.setdefault('result', Result.passed)
    kwargs.setdefault('duration', random.randint(10000, 100000))
    kwargs.setdefault('target', uuid4().hex)

    if 'source' not in kwargs:
        kwargs['source'] = source(project.repository)

    kwargs['project'] = project
    kwargs['project_id'] = kwargs['project'].id
    kwargs['author_id'] = kwargs['author'].id

    build = Build(**kwargs)
    db.session.add(build)

    event = Event(
        type=EventType.green_build,
        item_id=build.id,
        data={'status': 'success'}
    )
    db.session.add(event)

    return build


def plan(project, **kwargs):
    if 'label' not in kwargs:
        kwargs['label'] = PLAN_NAMES.next()

    plan = Plan.query.filter(
        Plan.label == kwargs['label'],
        Plan.project_id == project.id,
    ).first()
    if plan:
        return plan

    result = Plan(project=project, **kwargs)
    db.session.add(result)

    return result


def job(build, change=None, **kwargs):
    kwargs.setdefault('project', build.project)
    kwargs.setdefault('label', get_sentences(1)[0][:128])
    kwargs.setdefault('status', Status.finished)
    kwargs.setdefault('result', Result.passed)
    kwargs.setdefault('duration', random.randint(10000, 100000))
    kwargs['source'] = build.source

    kwargs['source_id'] = kwargs['source'].id
    kwargs['project_id'] = kwargs['project'].id
    kwargs['build_id'] = build.id
    if change:
        kwargs['change_id'] = change.id

    job = Job(
        build=build,
        change=change,
        **kwargs
    )
    db.session.add(job)

    node, created = get_or_create(Node, where={
        'label': get_sentences(1)[0][:32],
    })

    if created:
        cluster, _ = get_or_create(Cluster, where={
            'label': get_sentences(1)[0][:32],
        })

        clusternode = ClusterNode(cluster=cluster, node=node)
        db.session.add(clusternode)

    jobplan = JobPlan.build_jobplan(plan(build.project), job)
    db.session.add(jobplan)

    phase1_setup = JobPhase(
        project=job.project, job=job,
        date_started=job.date_started,
        date_finished=job.date_finished,
        status=Status.finished, result=Result.passed, label='Setup',
    )
    db.session.add(phase1_setup)

    phase1_compile = JobPhase(
        project=job.project, job=job,
        date_started=job.date_started,
        date_finished=job.date_finished,
        status=Status.finished, result=Result.passed, label='Compile',
    )
    db.session.add(phase1_compile)

    phase1_test = JobPhase(
        project=job.project, job=job,
        date_started=job.date_started,
        date_finished=job.date_finished,
        status=kwargs['status'], result=kwargs['result'], label='Test',
    )
    db.session.add(phase1_test)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_setup, status=phase1_setup.status, result=phase1_setup.result,
        label='Setup', node=node,
    )
    db.session.add(step)
    command = Command(
        jobstep=step,
        script="echo 1",
        label="echo 1",
    )
    db.session.add(command)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_compile, status=phase1_compile.status, result=phase1_compile.result,
        label='Compile', node=node,
    )
    db.session.add(step)
    command = Command(
        jobstep=step,
        script="echo 2",
        label="echo 2",
    )
    db.session.add(command)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_test, status=phase1_test.status, result=phase1_test.result,
        label=TEST_STEP_LABELS.next(), node=node,
    )
    db.session.add(step)
    command = Command(
        jobstep=step,
        script="echo 3",
        label="echo 3",
    )
    db.session.add(command)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_test, status=phase1_test.status, result=phase1_test.result,
        label=TEST_STEP_LABELS.next(), node=node,
    )
    db.session.add(step)
    command = Command(
        jobstep=step,
        script="echo 4",
        label="echo 4",
    )
    db.session.add(command)

    if phase1_test.result == Result.failed:
        db.session.add(FailureReason(
            reason='test_failures',
            build_id=build.id,
            job_id=job.id,
            step_id=step.id,
            project_id=job.project_id
        ))

    return job


def logchunk(source, **kwargs):
    # TODO(dcramer): we should default offset to previous entry in LogSource
    kwargs.setdefault('offset', 0)

    text = kwargs.pop('text', None) or '\n'.join(get_sentences(4))

    logchunk = LogChunk(
        source=source,
        job=source.job,
        project=source.project,
        text=text,
        size=len(text),
        **kwargs
    )
    db.session.add(logchunk)
    return logchunk


def revision(repository, author, message=None):
    message = message or '\n\n'.join(get_paragraphs(2))
    result = Revision(
        repository=repository, sha=uuid4().hex, author=author,
        repository_id=repository.id, author_id=author.id,
        message=message,
        branches=['default', 'foobar'],
    )
    db.session.add(result)

    return result


def _generate_random_coverage_string(num_lines):
    cov_str = ''
    for i in range(num_lines):
        rand_int = random.randint(0, 2)
        if rand_int == 0:
            cov_str += 'U'
        elif rand_int == 1:
            cov_str += 'N'
        elif rand_int == 2:
            cov_str += 'C'

    return cov_str


def _generate_sample_coverage_data(diff):
    diff_lines = diff.splitlines()

    cov_data = {}
    current_file = None
    line_number = None
    max_line_for_current_file = 0

    # For each file in the diff, generate random coverage info for lines up to
    # the maximum line present in the diff.
    for line in diff_lines:
        if line.startswith('diff'):
            if current_file is not None:
                cov_data[current_file] = _generate_random_coverage_string(
                    max_line_for_current_file)
            max_line_for_current_file = 0
            current_file = None
            line_number = None
        elif current_file is None and line_number is None and (line.startswith('+++') or line.startswith('---')):
            if line.startswith('+++ b/'):
                line = line.split('\t')[0]
                current_file = unicode(line[6:])
        elif line.startswith('@@'):
            line_num_info = line.split('+')[1]
            line_num_info = line_num_info.replace('@@', '')

            if ',' in line_num_info:
                line_number = int(line_num_info.split(',')[0])
                additional_lines = int(line_num_info.split(',')[1])
                max_line_for_current_file = line_number + additional_lines
            else:
                line_number = int(line_num_info)
                max_line_for_current_file = line_number

        else:
            # Just keep truckin...
            pass

    cov_data[current_file] = _generate_random_coverage_string(
        max_line_for_current_file)
    return cov_data


def file_coverage(project, job, patch):
    file_cov = _generate_sample_coverage_data(patch.diff)

    for file, coverage in file_cov.iteritems():
        file_coverage = FileCoverage(
            project_id=project.id,
            job_id=job.id,
            filename=file,
            data=coverage,
            lines_covered=5,
            lines_uncovered=8,
            diff_lines_covered=3,
            diff_lines_uncovered=5,
        )
        db.session.add(file_coverage)

    return file_coverage


def patch(project, **kwargs):
    kwargs.setdefault('diff', SAMPLE_DIFF)

    patch = Patch(
        repository=project.repository,
        **kwargs
    )
    db.session.add(patch)

    return patch


def source(repository, **kwargs):
    if not kwargs.get('revision_sha'):
        kwargs['revision_sha'] = revision(repository, author()).sha

    source = Source(repository=repository, **kwargs)
    db.session.add(source)

    return source


def test_result(jobstep, **kwargs):
    if 'name' not in kwargs:
        kwargs['name'] = TEST_FULL_NAMES.next()

    if 'duration' not in kwargs:
        kwargs['duration'] = random.randint(0, 3000)

    kwargs.setdefault('result', Result.passed)

    result = TestResult(step=jobstep, **kwargs)

    return result
