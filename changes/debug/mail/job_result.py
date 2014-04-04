from flask import render_template
from flask.views import MethodView
from jinja2 import Markup

from changes.models import Job
from changes.listeners.mail import MailNotificationHandler
from pynliner import Pynliner


class JobResultMailView(MethodView):
    def get(self, job_id):
        job = Job.query.get(job_id)

        assert job

        handler = MailNotificationHandler()

        parent = handler.get_parent(job)
        context = handler.get_context(job, parent)

        html_content = Markup(Pynliner().from_string(
            render_template('listeners/mail/notification.html', **context)
        ).run())

        return render_template('debug/email.html', html_content=html_content)
