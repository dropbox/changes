from flask import render_template
from jinja2 import Markup

from changes.api.base import MethodView
from changes.models import Project
from changes.reports.build import BuildReport

from pynliner import Pynliner


class BuildReportMailView(MethodView):
    def get(self, path=''):
        projects = Project.query.all()

        report = BuildReport(projects)

        context = report.generate()

        html_content = Markup(Pynliner().from_string(
            render_template('email/build_report.html', **context)
        ).run())

        return render_template('debug/email.html', html_content=html_content)
