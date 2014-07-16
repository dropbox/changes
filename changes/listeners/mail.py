from __future__ import absolute_import, print_function

import toronado

from flask import current_app, render_template
from flask_mail import Message, sanitize_address
from jinja2 import Markup

from changes.api.build_details import get_failure_reasons
from changes.config import db, mail
from changes.constants import Result
from changes.db.utils import try_create
from changes.listeners.notification_base import NotificationHandler
from changes.models import Event, EventType, JobPlan, ProjectOption
from changes.utils.http import build_uri


def filter_recipients(email_list, domain_whitelist=None):
    if domain_whitelist is None:
        domain_whitelist = current_app.config['MAIL_DOMAIN_WHITELIST']

    if not domain_whitelist:
        return email_list

    return [
        e for e in email_list
        if e.split('@', 1)[-1] in domain_whitelist
    ]


class MailNotificationHandler(NotificationHandler):
    def get_context(self, job, parent=None):
        test_failures = self.get_test_failures(job)
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        build = job.build

        result_label = self.get_result_label(job, parent)

        subject = u"{target} {result} - {project} #{number}".format(
            number='{0}.{1}'.format(job.build.number, job.number),
            result=result_label,
            target=build.target or build.source.revision_sha or 'Build',
            project=job.project.name,
        )

        build.uri = build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
        job.uri = build.uri + 'jobs/{0}/'.format(job.id.hex)

        for testgroup in test_failures:
            testgroup.uri = job.uri + 'tests/{0}/'.format(testgroup.id.hex)

        is_failure = job.result == Result.failed

        context = {
            'title': subject,
            'job': job,
            'build': job.build,
            'is_failure': is_failure,
            'is_passing': job.result == Result.passed,
            'result_label': result_label,
            'total_test_failures': num_test_failures,
            'test_failures': test_failures,
            'failure_reasons': get_failure_reasons(build),
        }

        if is_failure:
            # try to find the last failing log
            log_sources = self.get_failing_log_sources(job)
            if len(log_sources) == 1:
                log_clipping = self.get_log_clipping(
                    log_sources[0], max_size=5000, max_lines=25)

                context['build_log'] = {
                    'text': log_clipping,
                    'name': log_sources[0].name,
                    'uri': '{0}logs/{1}/'.format(job.uri, log_sources[0].id.hex),
                }
            elif log_sources:
                context['relevant_logs'] = [
                    {
                        'name': source.name,
                        'uri': '{0}logs/{1}/'.format(job.uri, source.id.hex),
                    } for source in log_sources
                ]

        return context

    def send(self, job, parent=None):
        # TODO(dcramer): we should send a clipping of a relevant job log
        recipients = filter_recipients(self.get_recipients(job))
        if not recipients:
            return

        event = try_create(Event, where={
            'type': EventType.email,
            'item_id': job.build_id,
            'data': {
                'recipients': recipients,
            }
        })
        if not event:
            # We've already sent out notifications for this build
            return

        context = self.get_context(job, parent)

        msg = Message(context['title'], recipients=recipients, extra_headers={
            'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
        })
        msg.body = render_template('listeners/mail/notification.txt', **context)
        msg.html = Markup(toronado.from_string(
            render_template('listeners/mail/notification.html', **context)
        ))

        mail.send(msg)

    def get_job_options(self, job):
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
        # TODO(dcramer): this should use snapshots of options
        jobplan = JobPlan.query.filter(
            JobPlan.job_id == job.id,
        ).first()
        if jobplan and 'snapshot' in jobplan.data:
            options.update(jobplan.data['snapshot']['options'])
        return options

    def get_recipients(self, job):
        options = self.get_job_options(job)

        recipients = []
        if options.get('mail.notify-author', '1') == '1':
            author = job.build.author
            if author:
                recipients.append(u'%s <%s>' % (author.name, author.email))

        if options.get('mail.notify-addresses'):
            recipients.extend(
                # XXX(dcramer): we dont have option validators so lets assume people
                # enter slightly incorrect values
                [x.strip() for x in options['mail.notify-addresses'].split(',')]
            )

        if not job.build.source.patch_id:
            if options.get('mail.notify-addresses-revisions'):
                recipients.extend(
                    [x.strip() for x in options['mail.notify-addresses-revisions'].split(',')]
                )

        return recipients


def job_finished_handler(*args, **kwargs):
    instance = MailNotificationHandler()
    instance.job_finished_handler(*args, **kwargs)
