from __future__ import absolute_import, division

import logging
from cStringIO import StringIO
from operator import add
from xml.parsers import expat
from lxml import etree

from flask import current_app

from changes.artifacts.xml import DelegateParser
from changes.config import statsreporter
from changes.constants import Result
from changes.models.testresult import TestResult, TestResultManager
from changes.utils.agg import aggregate_result
from changes.utils.http import build_web_uri

from .base import ArtifactHandler, ArtifactParseError


class XunitHandler(ArtifactHandler):
    FILENAMES = ('xunit.xml', 'junit.xml', 'nosetests.xml', '*.xunit.xml', '*.junit.xml', '*.nosetests.xml')
    logger = logging.getLogger('xunit')

    def process(self, fp, artifact):

        # TEMPORARY: run both handlers and compare the results
        # In the future, we should only call self.get_tests(fp)
        contents = fp.read()
        test_list = XunitHandlerEtree(self.step).get_tests(StringIO(contents))

        new_test_list = self.get_tests(StringIO(contents))
        if not compare_results(new_test_list, test_list):
            uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
            self.logger.warning('Different XML parse results; (step=%s, build=%s)',
                                self.step.id.hex, uri, exc_info=True)

        manager = TestResultManager(self.step)
        manager.save(test_list)

        return test_list

    @statsreporter.timer('xunithandler_get_tests')
    def get_tests(self, fp):
        try:
            parser = XunitDelegate(self.step)
            return parser.parse(fp)
        except Exception:
            uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
            self.logger.warning('Failed to parse XML; (step=%s, build=%s)',
                                self.step.id.hex, uri, exc_info=True)
            # TEMPORARY: don't call this, as we're also running the etree handler
            # self.report_malformed()
            return []


class XunitDelegate(DelegateParser):
    """
    Main delegating class to parse Xunit files: decides on the appropriate parser depending on the first tag
    """

    def __init__(self, step):
        super(XunitDelegate, self).__init__()
        self.step = step

        self._parser = expat.ParserCreate()
        self._parser.StartElementHandler = self.start
        self._parser.CharacterDataHandler = self.data
        self._parser.EndElementHandler = self.end

    def parse(self, fp):
        # Somehow this is much faster than ParseFile (up to 100x vs `ParseFile(StringIO(contents))`)
        # This might become a memory issue, in which case it's easy to switch back
        contents = fp.read()
        self._parser.Parse(contents, True)
        if not isinstance(self._subparser, XunitBaseParser):
            raise ArtifactParseError('Empty file found')
        results = _deduplicate_testresults(self._subparser.results)
        return results

    def _start(self, tag, attrs):
        if tag == 'unittest-results':
            self._set_subparser(BittenParser(self.step, self._parser))
            statsreporter.stats().incr('new_bitten_result_file')
        else:
            self._set_subparser(XunitParser(self.step, self._parser))
            statsreporter.stats().incr('new_xunit_result_file')
        self._parser.StartElementHandler(tag, attrs)


class XunitBaseParser(object):
    """
    Base class for Xunit parsers
    """

    def __init__(self, step, parser):
        self.step = step
        self._parser = parser

        self.results = []
        self._current_result = None
        self._is_message = False

    def start_message(self):
        self._current_result.message = ''
        self._is_message = True

    def process_message(self, data):
        self._current_result.message += data

    def close_message(self):
        # We truncate before deduplication; this gives us a weaker guarantee on maximum size,
        # but ensures that we have at least some message from each test.
        message_limit = current_app.config.get('TEST_MESSAGE_MAX_LEN')
        self._current_result.message = _truncate_message(self._current_result.message, message_limit)
        self._is_message = False


class BittenParser(XunitBaseParser):

    def start(self, tag, attrs):
        # Spec: http://bitten.edgewall.org/wiki/Documentation/reports.html
        if tag == 'unittest-results':
            pass
        elif tag == 'test':
            if attrs['status'] == 'success':
                result = Result.passed
            elif attrs['status'] == 'skipped':
                result = Result.skipped
            elif attrs['status'] in ('error', 'failure'):
                result = Result.failed
            else:
                result = None

            # no matching status tags were found
            if result is None:
                result = Result.passed

            self._current_result = TestResult(
                step=self.step,
                name=attrs['name'],
                package=attrs.get('fixture') or None,
                duration=float(attrs['duration']) * 1000,
                message='',
                result=result,
            )
        elif tag == 'traceback':
            self.start_message()

    def data(self, data):
        if self._is_message:
            self.process_message(data)

    def end(self, tag):
        if self._is_message:
            self.close_message()
        if tag == 'unittest-results':
            pass
        elif tag == 'test':
            self.results.append(self._current_result)
            self._current_result = None
        elif tag == 'traceback':
            pass


class XunitParser(XunitBaseParser):

    def __init__(self, step, parser):
        super(XunitParser, self).__init__(step, parser)
        self._test_is_quarantined = None

    def start(self, tag, attrs):
        # Spec: http://windyroad.com.au/dl/Open%20Source/JUnit.xsd
        if tag == 'testsuites':
            pass
        elif tag == 'testsuite':
            pass
        elif tag == 'testcase':
            # If there's a previous failure in addition to stdout or stderr,
            # prioritize showing the previous failure because that's what's
            # useful for debugging flakiness.
            message = attrs.get('last_failure_output') or None

            # Results are found in children elements
            # Default result is passing
            result = Result.passed

            if attrs.get('quarantined'):
                self._test_is_quarantined = True
            else:
                self._test_is_quarantined = False

            owner = attrs.get('owner', None)

            if attrs.get('time'):
                duration = float(attrs['time']) * 1000
            else:
                duration = None

            if not attrs.get('name'):
                raise ArtifactParseError('testcase is missing required "name" property.')

            self._current_result = TestResult(
                step=self.step,
                name=attrs['name'],
                package=attrs.get('classname') or None,
                duration=duration,
                result=result,
                reruns=int(attrs.get('rerun')) if attrs.get('rerun') else None,
                message=message,
                owner=owner,
            )
        elif tag == 'test-artifacts':
            if self._current_result is None:
                raise ArtifactParseError('test-artifacts not contained in testcase')
            if self._current_result.artifacts is None:
                self._current_result.artifacts = []
        elif tag == 'artifact':
            if self._current_result is None:
                raise ArtifactParseError('artifact not contained in testcase')
            if self._current_result.artifacts is None:
                raise ArtifactParseError('artifact not contained in test-artifacts list')
            self._current_result.artifacts.append(attrs)
        elif self._current_result is not None:
            # We are in a result message
            if tag == 'failure':
                self._current_result.result = Result.failed
            elif tag == 'skipped':
                self._current_result.result = Result.skipped
            elif tag == 'error':
                self._current_result.result = Result.failed

            if self._current_result.message is None:
                self.start_message()

    def data(self, data):
        if self._is_message:
            self.process_message(data)

    def end(self, tag):
        if self._is_message:
            self.close_message()
        if tag == 'testsuites' or tag == 'testsuite':
            pass
        elif tag == 'testcase':
            if self._test_is_quarantined:
                if self._current_result.result == Result.passed:
                    self._current_result.result = Result.quarantined_passed
                elif self._current_result.result == Result.failed:
                    self._current_result.result = Result.quarantined_failed
                elif self._current_result.result == Result.skipped:
                    self._current_result.result = Result.quarantined_skipped
            self._test_is_quarantined = None
            self.results.append(self._current_result)
            self._current_result = None
        elif tag == 'test-artifacts':
            pass
        elif tag == 'artifact':
            pass


class XunitHandlerEtree(ArtifactHandler):
    """
    Old Xunit handler, only kept for verification
    """
    FILENAMES = ('xunit.xml', 'junit.xml', 'nosetests.xml', '*.xunit.xml', '*.junit.xml', '*.nosetests.xml')
    logger = logging.getLogger('xunit')

    def process(self, fp, artifact):
        test_list = self.get_tests(fp)

        manager = TestResultManager(self.step)
        manager.save(test_list)

        return test_list

    @statsreporter.timer('xunithandler_get_tests')
    def get_tests(self, fp):
        content_size = None
        try:
            # libxml has a limit on the size of a text field by default, but we encode stdout/stderr.
            #
            # Its not good to have such huge text fields in the first place but we still want to
            # avoid hard failing here if we do.
            parser = etree.XMLParser(huge_tree=True)
            content = fp.read()
            content_size = len(content)
            root = etree.fromstring(content, parser=parser)
        except Exception:
            uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
            self.logger.warning('Failed to parse XML; (step=%s, build=%s, size=%s)',
                                self.step.id.hex, uri, content_size, exc_info=True)
            self.report_malformed()
            return []

        # We've parsed the XML successful, but we still need to make sure it is well-formed for our reasons.
        try:
            if root.tag == 'unittest-results':
                return self.get_bitten_tests(root)
            return self.get_xunit_tests(root)
        except ArtifactParseError:
            # There may be valid test data to be extracted, but we discard them all to be safe.
            self.report_malformed()
            return []

    def get_bitten_tests(self, root):
        step = self.step

        results = []

        message_limit = current_app.config.get('TEST_MESSAGE_MAX_LEN')
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
                message=_truncate_message(message, message_limit),
            ))

        return results

    def get_xunit_tests(self, root):
        step = self.step

        message_limit = current_app.config.get('TEST_MESSAGE_MAX_LEN')
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

            # If there's a previous failure in addition to stdout or stderr,
            # prioritize showing the previous failure because that's what's
            # useful for debugging flakiness.
            message = attrs.get("last_failure_output") or message
            # no matching status tags were found
            if result is None:
                result = Result.passed

            if attrs.get('quarantined'):
                if result == Result.passed:
                    result = Result.quarantined_passed
                elif result == Result.failed:
                    result = Result.quarantined_failed
                elif result == Result.skipped:
                    result = Result.quarantined_skipped

            owner = attrs.get('owner', None)

            if attrs.get('time'):
                duration = float(attrs['time']) * 1000
            else:
                duration = None

            if not attrs.get('name'):
                raise ArtifactParseError('testcase is missing required "name" property.')

            results.append(TestResult(
                step=step,
                name=attrs['name'],
                package=attrs.get('classname') or None,
                duration=duration,
                result=result,
                # We truncate before deduplication; this gives us a weaker guarantee on maximum size,
                # but ensures that we have at least some message from each test.
                message=_truncate_message(message, message_limit),
                reruns=int(attrs.get('rerun')) if attrs.get('rerun') else None,
                artifacts=self._get_testartifacts(node),
                owner=owner,
            ))

        results = _deduplicate_testresults(results)
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


def _deduplicate_testresults(results):
    """Combine TestResult objects until every package+name is unique.

    The traditions surrounding jUnit do not prohibit a single test from
    producing two or more <testcase> elements.  In fact, py.test itself
    will produce two such elements for a single test if the test both
    fails and then hits an error during tear-down.  To impedance-match
    this situation with the Changes constraint of one result per test,
    we combine <testcase> elements that belong to the same test.

    """
    result_dict = {}
    deduped = []

    for result in results:
        key = (result.package, result.name)
        existing_result = result_dict.get(key)

        if existing_result is not None:
            e, r = existing_result, result
            e.duration = _careful(add, e.duration, r.duration)
            e.result = aggregate_result((e.result, r.result))
            if e.message is None:
                e.message = ''
            if r.message is None:
                r.message = ''
            e.message += '\n\n' + r.message
            e.reruns = _careful(max, e.reruns, r.reruns)
            e.artifacts = _careful(add, e.artifacts, r.artifacts)
        else:
            result_dict[key] = result
            deduped.append(result)

    return deduped


def _careful(op, a, b):
    """Return `op(a, b)` if neither is `None`, else the non-`None` value."""
    if a is None:
        return b
    if b is None:
        return a
    return op(a, b)


_TRUNCATION_HEADER = " -- CONTENT TRUNCATED; Look for original XML file for the full data. --\n"


def _truncate_message(msg, limit):
    """Truncate a message if necessary, retaining as many ending lines as possible.
    If truncated, a header line explaining may be prepended to the beginning.

    Args:
        msg (str): The message to potentially truncate.
        limit (Optional[int]): Maximum number of bytes to retain of the message.
    """
    if msg is None or len(msg) <= limit:
        return msg
    nl = msg.find('\n', len(msg) - limit)
    if nl == -1:
        msg = ''  # No line ending? This message is going to be unreadable.
    else:
        msg = msg[nl + 1:]
    return _TRUNCATION_HEADER + msg


def compare_results(results1, results2):
    if not len(results1) == len(results2):
        return False
    for res1, res2 in zip(results1, results2):
        if not (
            res1.step == res2.step and
            res1._name == res2._name and
            res1._package == res2._package and
            (res1.message or '') == (res2.message or '') and
            res1.result == res2.result and
            res1.duration == res2.duration and
            res1.reruns == res2.reruns and
            res1.artifacts == res2.artifacts and
            res1.owner == res2.owner
        ):
            return False
    return True
