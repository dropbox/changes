from __future__ import absolute_import, division

from lxml import etree

from changes.config import db
from changes.constants import Result
from changes.models import TestResult, TestResultManager

from .base import ArtifactHandler


class XunitHandler(ArtifactHandler):
    def process(self, fp):
        test_list = self.get_tests(fp)

        manager = TestResultManager(self.job)
        with db.session.begin_nested():
            manager.save(test_list)

        return test_list

    def get_tests(self, fp):
        # TODO(dcramer): needs to handle TestSuite's
        job = self.job
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

            results.append(TestResult(
                job=job,
                name=attrs['name'],
                package=attrs['classname'] or None,
                duration=float(attrs['time']),
                result=result,
                message=message,
            ))

        return results
