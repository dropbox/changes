from flask import render_template
from flask.views import MethodView

from changes.models.build import Build
from changes.listeners.mail import MailNotificationHandler


class BuildResultMailView(MethodView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        assert build, 'There is no build for {}'.format(build_id)

        builds = list(
            Build.query.filter(Build.collection_id == build.collection_id))
        notification_handler = MailNotificationHandler()
        context = notification_handler.get_collection_context(builds)
        msg = notification_handler.get_msg(context)
        return render_template(
            'debug/email.html',
            recipients=msg.recipients,
            subject=msg.subject,
            text_content=msg.body,
            html_content=msg.html,
        )
