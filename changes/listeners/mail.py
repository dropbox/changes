from __future__ import absolute_import, print_function

from flask import render_template
from flask_mail import Message, sanitize_address

from changes.config import db, mail
from changes.constants import Result
from changes.listeners.notification_base import NotificationHandler
from changes.models import JobPlan, ProjectOption, ItemOption
from changes.utils.http import build_uri


class MailNotificationHandler(NotificationHandler):
    def get_context(self, job, parent=None):
        test_failures = self.get_test_failures(job)
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        build = job.build

        result_label = self.get_result_label(job, parent)

        subject = u"Build {result} - {project} #{number} ({target})".format(
            number='{0}.{1}'.format(job.build.number, job.number),
            result=result_label,
            target=build.target or build.source.revision_sha or 'Unknown',
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
            'result_label': result_label,
            'total_test_failures': num_test_failures,
            'test_failures': test_failures,
        }

        if is_failure:
            # try to find the last failing log
            primary_log = self.get_primary_log_source(job)
            if primary_log:
                log_clipping = self.get_log_clipping(
                    primary_log, max_size=5000, max_lines=25)

                context['build_log'] = {
                    'text': log_clipping,
                    'name': primary_log.name,
                    'uri': '{0}logs/{1}/'.format(job.uri, primary_log.id.hex),
                }

        return context

    def send(self, job, parent=None):
        # TODO(dcramer): we should send a clipping of a relevant job log
        recipients = self.get_recipients(job)
        if not recipients:
            return

        context = self.get_context(job, parent)

        msg = Message(context['title'], recipients=recipients, extra_headers={
            'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
        })
        msg.body = render_template('listeners/mail/notification.txt', **context)
        msg.html = render_template('listeners/mail/notification.html', **context)

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
