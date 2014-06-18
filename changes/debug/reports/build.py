import toronado

from flask import render_template, request
from flask.views import MethodView
from jinja2 import Markup

from changes.models import Project
from changes.reports.build import BuildReport


class BuildReportMailView(MethodView):
    def get(self, path=''):
        projects = Project.query.all()

        report = BuildReport(projects)

        context = report.generate(days=int(request.args.get('days', 7)))

        html_content = Markup(toronado.from_string(
            render_template('email/build_report.html', **context)
        ))

        return render_template('debug/email.html', html_content=html_content)
