from __future__ import absolute_import, print_function

from flask import render_template
from flask_mail import Message, sanitize_address

from changes.config import db, mail
from changes.constants import Result, Status
from changes.models import (
    Job, JobPlan, TestGroup, ProjectOption, LogSource, LogChunk, ItemOption
)
from changes.utils.http import build_uri


def get_test_failures(job):
    return sorted([t.name_sha for t in db.session.query(
        TestGroup.name_sha,
    ).filter(
        TestGroup.job_id == job.id,
        TestGroup.result == Result.failed,
        TestGroup.num_leaves == 0,
    )])


def did_cause_breakage(job):
    """
    Compare with parent job (previous job) and confirm if current
    job provided any change in state (e.g. new failures).
    """
    if job.result != Result.failed:
        return False

    parent = Job.query.filter(
        Job.revision_sha != None,  # NOQA
        Job.patch_id == None,
        Job.revision_sha != job.revision_sha,
        Job.date_created < job.date_created,
        Job.status == Status.finished,
    ).order_by(Job.date_created.desc()).first()

    # if theres no parent, this job must be at fault
    if parent is None:
        return True

    if parent.result == Result.passed:
        return True

    current_failures = get_test_failures(job)
    # if we dont have any testgroup failures, then we cannot identify the cause
    # so we must notify the individual
    if not current_failures:
        return True

    parent_failures = get_test_failures(parent)
    if parent_failures != current_failures:
        return True

    return False


def get_log_clipping(logsource, max_size=5000, max_lines=25):
    queryset = LogChunk.query.filter(
        LogChunk.source_id == logsource.id,
    )
    tail = queryset.order_by(LogChunk.offset.desc()).limit(1).first()

    chunks = list(queryset.filter(
        (LogChunk.offset + LogChunk.size) >= max(tail.offset - max_size, 0),
    ).order_by(LogChunk.offset.asc()))

    clipping = ''.join(l.text for l in chunks).strip()[-max_size:]
    # only return the last 25 lines
    clipping = '\r\n'.join(clipping.splitlines()[-max_lines:])

    return clipping


def send_notification(job, recipients):
    # TODO(dcramer): we should send a clipping of a relevant job log
    test_failures = TestGroup.query.filter(
        TestGroup.job_id == job.id,
        TestGroup.result == Result.failed,
        TestGroup.num_leaves == 0,
    ).order_by(TestGroup.name.asc())
    num_test_failures = test_failures.count()
    test_failures = test_failures[:25]

    # TODO(dcramer): we should probably find a better way to do logs
    primary_log = LogSource.query.filter(
        LogSource.job_id == job.id,
    ).order_by(LogSource.date_created.asc()).first()
    if primary_log:
        log_clipping = get_log_clipping(
            primary_log, max_size=5000, max_lines=25)

    subject = u"Build {result} - {project} #{number} ({target})".format(
        number='{0}.{1}'.format(job.build.number, job.number),
        result=unicode(job.result),
        target=job.target or job.revision_sha or 'Unknown',
        project=job.project.name,
    )

    for testgroup in test_failures:
        testgroup.uri = build_uri('/testgroups/{0}/'.format(testgroup.id.hex))

    job.uri = build_uri('/jobs/{0}/'.format(job.id.hex))

    context = {
        'job': job,
        'build': job.build,
        'total_test_failures': num_test_failures,
        'test_failures': test_failures,
    }

    if primary_log:
        context['build_log'] = {
            'text': log_clipping,
            'name': primary_log.name,
            'link': '{0}logs/{1}/'.format(job.uri, primary_log.id.hex),
        }

    msg = Message(subject, recipients=recipients, extra_headers={
        'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
    })
    msg.body = render_template('listeners/mail/notification.txt', **context)
    msg.html = render_template('listeners/mail/notification.html', **context)

    mail.send(msg)


def get_job_options(job):
    option_names = [
        'mail.notify-author',
        'mail.notify-addresses',
        'mail.notify-addresses-revisions',
    ]

    # get relevant options
    options = dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == job.project_id,
            ProjectOption.name.in_(option_names),
        )
    )

    # if a plan was specified, it's options override the project's
    job_plan = JobPlan.query.filter(
        JobPlan.job_id == job.id,
    ).first()
    if job_plan:
        plan_options = db.session.query(
            ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id == job_plan.plan_id,
            ItemOption.name.in_(option_names),
        )
        # determine plan options
        for key, value in plan_options:
            options[key] = value

    return options


def job_finished_handler(job, **kwargs):
    options = get_job_options(job)

    recipients = []
    if options.get('mail.notify-author', '1') == '1':
        author = job.author
        if author:
            recipients.append(u'%s <%s>' % (author.name, author.email))

    if options.get('mail.notify-addresses'):
        recipients.extend(
            # XXX(dcramer): we dont have option validators so lets assume people
            # enter slightly incorrect values
            [x.strip() for x in options['mail.notify-addresses'].split(',')]
        )

    if not job.patch_id:
        if options.get('mail.notify-addresses-revisions'):
            recipients.extend(
                [x.strip() for x in options['mail.notify-addresses-revisions'].split(',')]
            )

    if not recipients:
        return

    if not did_cause_breakage(job):
        return

    send_notification(job, recipients)
