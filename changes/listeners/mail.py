from __future__ import absolute_import, print_function

from flask import current_app, render_template
from flask_mail import Message, sanitize_address

from changes.config import db, mail
from changes.constants import Result, Status
from changes.models import Build, TestGroup, ProjectOption, LogSource, LogChunk


def build_uri(path):
    return str('{base_uri}/{path}'.format(
        base_uri=current_app.config['BASE_URI'].rstrip('/'),
        path=path.lstrip('/'),
    ))


def get_test_failures(build):
    return sorted([t.name_sha for t in db.session.query(
        TestGroup.name_sha,
    ).filter(
        TestGroup.build_id == build.id,
        TestGroup.result == Result.failed,
        TestGroup.num_leaves == 0,
    )])


def did_cause_breakage(build):
    """
    Compare with parent build (previous build) and confirm if current
    build provided any change in state (e.g. new failures).
    """
    if build.result != Result.failed:
        return False

    parent = Build.query.filter(
        Build.revision_sha != None,  # NOQA
        Build.patch_id == None,
        Build.revision_sha != build.revision_sha,
        Build.date_created < build.date_created,
        Build.status == Status.finished,
    ).order_by(Build.date_created.desc()).first()

    # if theres no parent, this build must be at fault
    if parent is None:
        return True

    if parent.result == Result.passed:
        return True

    current_failures = get_test_failures(build)
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
    ).order_by(LogChunk.offset.desc())
    tail = queryset.limit(1).first()

    chunks = list(queryset.filter(
        LogChunk.offset <= tail.offset,
        (LogChunk.offset + LogChunk.size) >= max(tail.offset - max_size, 0),
    ).order_by(LogChunk.offset.asc()))

    clipping = ''.join(l.text for l in chunks)[-max_size:]
    # only return the last 25 lines
    clipping = '\r\n'.join(clipping.splitlines()[-max_lines:])

    return clipping


def send_notification(build, recipients):
    # TODO(dcramer): we should send a clipping of a relevant build log
    test_failures = TestGroup.query.filter(
        TestGroup.build_id == build.id,
        TestGroup.result == Result.failed,
        TestGroup.num_leaves == 0,
    ).order_by(TestGroup.name.asc())
    num_test_failures = test_failures.count()
    test_failures = test_failures[:25]

    # TODO(dcramer): we should probably find a better way to do logs
    primary_log = LogSource.query.filter(
        LogSource.build_id == build.id,
    ).order_by(LogSource.date_created.asc()).first()
    if primary_log:
        log_clipping = get_log_clipping(
            primary_log, max_size=5000, max_lines=50)

    subject = u"Build {result} - {target} ({project})".format(
        result=unicode(build.result),
        target=build.target or build.revision_sha or 'Unknown',
        project=build.project.name,
    )

    for testgroup in test_failures:
        testgroup.uri = build_uri('/testgroups/{0}/'.format(testgroup.id.hex))

    build.uri = build_uri('/builds/{0}/'.format(build.id.hex))

    context = {
        'build': build,
        'total_test_failures': num_test_failures,
        'test_failures': test_failures,
    }

    if primary_log:
        context['build_log'] = {
            'text': log_clipping,
            'name': primary_log.name,
            'link': '{0}logs/{1}/'.format(build.uri, primary_log.id.hex),
        }

    msg = Message(subject, recipients=recipients, extra_headers={
        'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
    })
    msg.body = render_template('listeners/mail/notification.txt', **context)
    msg.html = render_template('listeners/mail/notification.html', **context)

    mail.send(msg)


def build_finished_handler(build, **kwargs):
    # get relevant options
    options = dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == build.project_id,
            ProjectOption.name.in_([
                'mail.notify-author', 'mail.notify-addresses',
                'mail.notify-addresses-revisions',
            ])
        )
    )

    recipients = []
    if options.get('mail.notify-author', '1') == '1':
        author = build.author
        if author:
            recipients.append(u'%s <%s>' % (author.name, author.email))

    if options.get('mail.notify-addresses'):
        recipients.extend(
            # XXX(dcramer): we dont have option validators so lets assume people
            # enter slightly incorrect values
            [x.strip() for x in options['mail.notify-addresses'].split(',')]
        )

    if not build.patch_id:
        if options.get('mail.notify-addresses-revisions'):
            recipients.extend(
                [x.strip() for x in options['mail.notify-addresses-revisions'].split(',')]
            )

    if not recipients:
        return

    if not did_cause_breakage(build):
        return

    send_notification(build, recipients)
