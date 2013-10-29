from __future__ import absolute_import, division

from hashlib import sha1
from lxml import etree

from changes.config import db
from changes.constants import Result
from changes.models.test import Test

from .base import ArtifactHandler


class XunitHandler(ArtifactHandler):
    def process(self, fp):
        results = self.get_tests(fp)

        with db.get_session() as session:
            for result in results:
                constraints = {
                    'build_id': result.build_id,
                    'project_id': result.project_id,
                    'label': result.label,
                }
                # TODO(cramer): this has a race condition
                if not Test.query.filter_by(**constraints).first():
                    session.add(result)

        return results

    def get_tests(self, fp):
        build = self.build
        root = etree.fromstring(fp.read())

        results = []
        for node in root.iter('testcase'):
            # classname, name, time
            attrs = dict(node.items())
            # AFAIK the spec says only one tag can be present
            # http://windyroad.com.au/dl/Open%20Source/JUnit.xsd
            try:
                r_node = list(node.iterchildren())[0]
            except IndexError:
                result = Result.passed
                message = ''
            else:
                # TODO(cramer): whitelist tags that are not statuses
                if r_node.tag == 'failure':
                    result = Result.failed
                elif r_node.tag == 'skipped':
                    result = Result.skipped
                elif r_node.tag == 'error':
                    result = Result.error
                else:
                    result = None

                message = r_node.text

            # no matching status tags were found
            if result is None:
                result = Result.passed

            results.append(Test(
                build_id=build.id,
                project_id=build.project_id,
                name=attrs['name'],
                package=attrs['classname'] or None,
                duration=float(attrs['time']),
                result=result,
                message=message,
            ))

        return results
