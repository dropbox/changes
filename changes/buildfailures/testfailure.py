from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure
from changes.utils.http import build_uri


class TestFailure(BuildFailure):
    def get_html_label(self, build):
        link = build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(build.project.slug, build.id.hex))

        try:
            test_failures = (
                s.value for s in build.stats if s.name == 'test_failures'
            ).next()
        except StopIteration:
            return Markup('There were an <a href="{link}">unknown number of test failures</a>.'.format(
                link=link,
            ))

        return Markup('There were <a href="{link}">{count} failing tests</a>.'.format(
            link=link,
            count=test_failures,
        ))
