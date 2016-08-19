from __future__ import absolute_import, print_function
from itertools import imap
import logging

import toronado

from email.utils import parseaddr
from flask import current_app, render_template
from flask_mail import Message, sanitize_address
from jinja2 import Markup

from changes.config import db, mail
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.lib import build_context_lib, build_type
from changes.models.event import Event, EventType
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobplan import JobPlan
from changes.models.project import ProjectOption


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


class MailNotificationHandler(object):
    logger = logging.getLogger('mail')

    def send(self, msg, build):
        msg.recipients = filter_recipients(msg.recipients)
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
        # If we were unable to create the Event, we must've done so (and thus sent the mail) already.
        if not event:
            self.logger.warning('An email has already been sent for collection_id=%s, (build_id=%s).',
                build.collection_id, build.id.hex)
            return

        mail.send(msg)

    def get_msg(self, builds):
        # type: (List[Build]) -> Message
        context = build_context_lib.get_collection_context(builds)
        if context['result'] == Result.passed:
            return None
        max_shown = current_app.config.get('MAX_SHOWN_ITEMS_PER_BUILD_MAIL', 3)
        context.update({
            'MAX_SHOWN_ITEMS_PER_BUILD': max_shown,
            'showing_failing_tests_count':
                sum([min(b['failing_tests_count'], max_shown) for b in context['builds']])
        })
        recipients = self.get_collection_recipients(context)

        msg = Message(context['title'], recipients=recipients, extra_headers={
            'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
        })
        msg.body = render_template('listeners/mail/notification.txt', **context)
        msg.html = Markup(toronado.from_string(
            render_template('listeners/mail/notification.html', **context)
        ))

        return msg

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
        if build_type.is_initial_commit_build(build):
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

    if not build.collection_id:
        # If there isn't a collection_id, assume the build stands alone.
        # All builds should probably have collection_id set.
        builds = [build]
    else:
        builds = list(
            Build.query.filter(Build.collection_id == build.collection_id))

    # Exit if there are no builds for the given build_id, or any build hasn't
    # finished.
    if not builds or any(map(lambda build: build.status != Status.finished, builds)):
        return

    notification_handler = MailNotificationHandler()
    msg = notification_handler.get_msg(builds)

    if msg is not None:
        notification_handler.send(msg, build)
