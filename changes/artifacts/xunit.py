from __future__ import absolute_import, division

import logging

from lxml import etree

from changes.config import db
from changes.constants import Result
from changes.db.utils import try_create
from changes.models import TestResult, TestResultManager, FailureReason

from .base import ArtifactHandler


class XunitHandler(ArtifactHandler):
    logger = logging.getLogger('xunit')

    def process(self, fp):
        test_list = self.get_tests(fp)

        manager = TestResultManager(self.step)
        manager.save(test_list)

        return test_list

    def get_tests(self, fp):
        try:
            root = etree.fromstring(fp.read())
        except Exception:
            # Record the JobStep ID so we have any hope of tracking these down.
            self.logger.exception('Failed to parse XML; (step={})'.format(self.step.id.hex))
            try_create(FailureReason, {
                'step_id': self.step.id,
                'job_id': self.step.job_id,
                'build_id': self.step.job.build_id,
                'project_id': self.step.project_id,
                'reason': 'malformed_artifact'
            })
            db.session.commit()
            return []

        if root.tag == 'unittest-results':
            return self.get_bitten_tests(root)
        return self.get_xunit_tests(root)

    def get_bitten_tests(self, root):
        step = self.step

        results = []

        # XXX(dcramer): bitten xml syntax, no clue what this
        for node in root.iter('test'):
            # classname, name, time
            attrs = dict(node.items())
            # AFAIK the spec says only one tag can be present
            # http://windyroad.com.au/dl/Open%20Source/JUnit.xsd
            if attrs['status'] == 'success':
                result = Result.passed
            elif attrs['status'] == 'skipped':
                result = Result.skipped
            elif attrs['status'] in ('error', 'failure'):
                result = Result.failed
            else:
                result = None

            try:
                message = list(node.iter('traceback'))[0].text
            except IndexError:
                message = ''

            # no matching status tags were found
            if result is None:
                result = Result.passed

            results.append(TestResult(
                step=step,
                name=attrs['name'],
                package=attrs.get('fixture') or None,
                duration=float(attrs['duration']) * 1000,
                result=result,
                message=message,
            ))

        return results

    def get_xunit_tests(self, root):
        step = self.step

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
                    result = Result.failed
                else:
                    result = None

                message = r_node.text

            # no matching status tags were found
            if result is None:
                result = Result.passed

            if attrs.get('time'):
                duration = float(attrs['time']) * 1000
            else:
                duration = None

            results.append(TestResult(
                step=step,
                name=attrs['name'],
                package=attrs.get('classname') or None,
                duration=duration,
                result=result,
                message=(message or attrs.get("last_failure_output") or ""),
                reruns=int(attrs.get('rerun')) if attrs.get('rerun') else None,
                artifacts=self._get_testartifacts(node)
            ))

        return results

    def _get_testartifacts(self, node):
        test_artifacts_node = node.find('test-artifacts')
        if test_artifacts_node is None:
            return None

        results = []
        for artifact_node in node.iter('artifact'):
            attrs = dict(artifact_node.items())
            results.append(attrs)
        return results
