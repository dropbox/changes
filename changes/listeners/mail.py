from __future__ import absolute_import, print_function
from itertools import imap
import logging
from changes.models.jobplan import JobPlan

import toronado

from email.utils import parseaddr
from flask import current_app, render_template
from flask_mail import Message, sanitize_address
from jinja2 import Markup

from changes.api.build_details import get_patch_parent_last_build
from changes.config import db, mail
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.models.event import Event, EventType
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobstep import JobStep
from changes.models.log import LogSource, LogChunk
from changes.models.project import ProjectOption
from changes.models.test import TestCase
from changes.utils.http import build_uri


def filter_recipients(email_list, domain_whitelist=None):
    """
    Returns emails from email_list that have been white-listed by
    domain_whitelist.
    """
    if domain_whitelist is None:
        domain_whitelist = current_app.config['MAIL_DOMAIN_WHITELIST']

    if not domain_whitelist:
        return email_list

    return [
        e for e in email_list
        if parseaddr(e)[1].split('@', 1)[-1] in domain_whitelist
    ]


def get_project_uri(build):
    return '/projects/{}/'.format(build.project.id.hex)


def get_source_uri(build, source):
    return '{}sources/{}/'.format(get_project_uri(build), source.id.hex)


def get_parent_uri(build, source):
    return '{}commits/{}/'.format(get_project_uri(build), source.revision_sha)


def get_build_uri(build):
    return '{}builds/{}/'.format(get_project_uri(build), build.id.hex)


def get_job_uri(job):
    return '{}jobs/{}/'.format(get_build_uri(job.build), job.id.hex)


def get_test_case_uri(test_case):
    return '{}tests/{}/'.format(get_job_uri(test_case.job), test_case.id.hex)


def get_log_uri(log_source):
    return '{}logs/{}/'.format(get_job_uri(log_source.job), log_source.id.hex)


def aggregate_count(items, key):
    return sum(map(lambda item: item[key], items))


class MailNotificationHandler(object):
    logger = logging.getLogger('mail')

    def send(self, msg, build):
        if not msg.recipients:
            self.logger.info(
                'Exiting for collection_id={} because its message has no '
                'recipients.'.format(build.collection_id))
            return

        event = try_create(Event, where={
            'type': EventType.email,
            'item_id': build.collection_id,
            'data': {
                'triggering_build_id': build.id.hex,
                'recipients': msg.recipients,
            }
        })
        assert event, 'An email has already been sent for collection_id={} (build_id={}).'.format(
            build.collection_id, build.id.hex)

        mail.send(msg)

    def get_msg(self, context):
        recipients = self.get_collection_recipients(context)

        msg = Message(context['title'], recipients=recipients, extra_headers={
            'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
        })
        msg.body = render_template('listeners/mail/notification.txt', **context)
        msg.html = Markup(toronado.from_string(
            render_template('listeners/mail/notification.html', **context)
        ))

        return msg

    def get_subject(self, target, label, result):
        # Use the first label line for multi line labels.
        if label:
            lines = label.splitlines()
            if len(lines) > 1:
                label = u"{}...".format(lines[0])

        format_dict = {
            'target': target,
            'label': label,
            'verb': str(result).lower(),
        }

        if target:
            return u"{target} {verb} - {label}".format(**format_dict)
        else:
            return u"Build {verb} - {label}".format(**format_dict)

    def get_collection_context(self, builds):
        """
        Given a non-empty list of finished builds, returns a context for
        rendering the build results email.
        """

        def sort_builds(builds_context):
            result_priority_order = (
                Result.passed,
                Result.skipped,
                Result.unknown,
                Result.aborted,
                Result.failed,
            )

            return sorted(
                builds_context,
                key=lambda build: (
                    result_priority_order.index(build['build'].result),
                    build['total_failing_tests_count'],
                    build['total_failing_logs_count']
                ),
                reverse=True
            )

        builds_context = sort_builds(map(self.get_build_context, builds))
        if all(map(lambda build: build['is_passing'], builds_context)):
            result = Result.passed
        elif any(imap(lambda build: build['is_failing'], builds_context)):
            result = Result.failed
        else:
            result = Result.unknown

        build = builds[0]
        target, target_uri = self.get_build_target(build)

        date_created = min([_build.date_created for _build in builds])

        return {
            'title': self.get_subject(target, build.label, result),
            'builds': builds_context,
            'result': result,
            'target_uri': target_uri,
            'target': target,
            'label': build.label,
            'date_created': date_created,
            'author': build.author,
            'commit_message': build.message or '',
            'failing_tests_count': aggregate_count(builds_context, 'failing_tests_count'),
            'total_failing_tests_count': aggregate_count(builds_context, 'total_failing_tests_count'),
        }

    def get_build_target(self, build):
        """
        Returns the build's target and target uri (normally a phabricator
        revision and diff url).
        """
        source_data = build.source.data or {}
        phabricator_rev_id = source_data.get('phabricator.revisionID')
        phabricator_uri = source_data.get('phabricator.revisionURL')

        if phabricator_rev_id and phabricator_uri:
            target = 'D{}'.format(phabricator_rev_id)
            target_uri = phabricator_uri
        else:
            # TODO: Make sure that the phabricator source data is present to
            # make this obsolete.
            target = None
            target_uri = build_uri(get_source_uri(build, build.source))
        return target, target_uri

    def get_build_context(self, build, get_parent=True):
        jobs = list(Job.query.filter(Job.build_id == build.id))
        jobs_context = map(self.get_job_context, jobs)

        parent_build_context = None
        if get_parent:
            parent_build = get_patch_parent_last_build(build)
            if parent_build:
                parent_build_context = self.get_build_context(
                    parent_build, get_parent=False)

        return {
            'build': build,
            'parent_build': parent_build_context,
            'jobs': jobs_context,
            'uri': build_uri(get_build_uri(build)),
            'is_passing': build.result == Result.passed,
            'is_failing': build.result == Result.failed,
            'result_string': str(build.result).lower(),
            'failing_tests_count': aggregate_count(jobs_context, 'failing_tests_count'),
            'total_failing_tests_count': aggregate_count(jobs_context, 'total_failing_tests_count'),
            'failing_logs_count': aggregate_count(jobs_context, 'failing_logs_count'),
            'total_failing_logs_count': aggregate_count(jobs_context, 'total_failing_logs_count'),
        }

    def get_job_context(self, job):

        def get_job_failing_tests(job):
            failing_tests = TestCase.query.filter(
                TestCase.job_id == job.id,
                TestCase.result == Result.failed,
            ).order_by(TestCase.name.asc())
            failing_tests_count = failing_tests.count()

            failing_tests = [
                {
                    'test_case': test_case,
                    'uri': build_uri(get_test_case_uri(test_case)),
                } for test_case in failing_tests[:3]
            ]

            return failing_tests, failing_tests_count

        def get_job_failing_log_sources(job):
            failing_log_sources = LogSource.query.filter(
                LogSource.job_id == job.id,
            ).join(
                JobStep, LogSource.step_id == JobStep.id,
            ).filter(
                JobStep.result == Result.failed,
            ).order_by(JobStep.date_created)
            failing_log_sources_count = failing_log_sources.count()

            failing_logs = []
            for log_source in failing_log_sources[:3]:
                log_clipping = self.get_log_clipping(
                    log_source, max_size=5000, max_lines=25)
                failing_logs.append({
                    'text': log_clipping,
                    'name': log_source.name,
                    'uri': build_uri(get_log_uri(log_source)),
                })

            return failing_logs, failing_log_sources_count

        failing_tests, failing_tests_count = get_job_failing_tests(job)
        failing_logs, failing_logs_count = get_job_failing_log_sources(job)

        context = {
            'job': job,
            'uri': build_uri(get_job_uri(job)),
            'failing_tests': failing_tests,
            'failing_tests_count': len(failing_tests),
            'total_failing_tests_count': failing_tests_count,
            'failing_logs': failing_logs,
            'failing_logs_count': len(failing_logs),
            'total_failing_logs_count': failing_logs_count,
        }

        return context

    def get_log_clipping(self, logsource, max_size=5000, max_lines=25):
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

    def get_collection_recipients(self, collection_context):
        """
        Returns a list of recipients for a collection context created by
        get_collection_context. Only recipients for failing builds will be
        returned.
        """
        recipient_lists = map(
            lambda build_context: self.get_build_recipients(build_context['build']),
            collection_context['builds'])
        return list(set([r for rs in recipient_lists for r in rs]))

    def get_build_recipients(self, build):
        """
        Returns a list of recipients for a build.

        The build author is included unless the build and all failing jobs
        have turned off the mail.notify-author option.

        Successful builds will only return the author.

        Recipients are also collected from each failing job's
        mail.notify-addresses and mail.notify-addresses-revisions options.
        Should there be no failing jobs (is that possible?), recipients are
        collected from the build's own mail.notify-addresses and
        mail.notify-addresses-revisions options.
        """
        recipients = []
        options = self.get_build_options(build)

        if options['mail.notify-author']:
            author = build.author
            if author:
                recipients.append(u'%s <%s>' % (author.name, author.email))

        if build.result == Result.passed:
            return recipients

        recipients.extend(options['mail.notify-addresses'])

        if not build.source.patch_id:
            recipients.extend(options['mail.notify-addresses-revisions'])

        return recipients

    def get_build_options(self, build):
        """
        Returns a build's mail options as a
        {
            'mail.notify-author': bool,
            'mail.notify-addresses': set,
            'mail.notify-addresses-revisions': set,
        } dict.

        The 'mail.notify-author' option is True unless the build and all
        failing jobs have turned off the mail.notify-author option.

        The mail.notify-addresses and mail.notify-addresses-revisions options
        respectively are sets of email addresses constructed by merging the
        corresponding options of all failing jobs. Note that the build's
        options are used as defaults when constructing the options for
        each job, so that the job options override the build options.

        Finally, the build's own options are used if there are no failing jobs.
        """
        default_options = {
            'mail.notify-author': '1',
            'mail.notify-addresses': '',
            'mail.notify-addresses-revisions': '',
        }

        build_options = dict(
            default_options,
            **dict(db.session.query(
                ProjectOption.name, ProjectOption.value
            ).filter(
                ProjectOption.project_id == build.project_id,
                ProjectOption.name.in_(default_options.keys()),
            ))
        )

        # Get options for all failing jobs.
        jobs_options = []
        for job in list(Job.query.filter(Job.build_id == build.id)):
            if job.result != Result.passed:
                jobs_options.append(dict(
                    build_options, **self.get_job_options(job)))

        # Merge all options.

        # Fallback to build options in case there are no failing jobs.
        all_options = jobs_options or [build_options]

        merged_options = {
            # Notify the author unless all jobs and the build have turned the
            # notify-author option off.
            'mail.notify-author': any(
                imap(
                    lambda options: options.get('mail.notify-author') == '1',
                    all_options,
                ),
            ),
            'mail.notify-addresses': set(),
            'mail.notify-addresses-revisions': set(),
        }

        recipient_keys = ['mail.notify-addresses', 'mail.notify-addresses-revisions']
        for options in all_options:
            for key in recipient_keys:
                # XXX(dcramer): we dont have option validators so lets assume
                # people enter slightly incorrect values
                merged_options[key] |= set(
                    [x.strip() for x in options[key].split(',') if x.strip()]
                )
        return merged_options

    def get_job_options(self, job):
        jobplan = JobPlan.query.filter(
            JobPlan.job_id == job.id,
        ).first()
        options = {}
        if jobplan and 'snapshot' in jobplan.data:
            options = jobplan.data['snapshot']['options']
        return options


def build_finished_handler(build_id, *args, **kwargs):
    build = Build.query.get(build_id)
    if not build:
        return

    builds = list(
        Build.query.filter(Build.collection_id == build.collection_id))

    # Exit if there are no builds for the given build_id, or any build hasn't
    # finished.
    if not builds or any(map(lambda build: build.status != Status.finished, builds)):
        return

    notification_handler = MailNotificationHandler()
    context = notification_handler.get_collection_context(builds)
    msg = notification_handler.get_msg(context)

    if context['result'] != Result.passed:
        notification_handler.send(msg, build)
