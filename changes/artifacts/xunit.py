from __future__ import absolute_import, division

import logging
from operator import add
from xml.parsers import expat
from xml.sax import saxutils

from flask import current_app

from changes.artifacts.xml import DelegateParser
from changes.config import statsreporter
from changes.constants import Result
from changes.models.testresult import TestResult, TestResultManager, TestSuite
from changes.utils.agg import aggregate_result
from changes.utils.http import build_web_uri

from .base import ArtifactHandler, ArtifactParseError


class XunitHandler(ArtifactHandler):
    FILENAMES = ('xunit.xml', 'junit.xml', 'nosetests.xml', '*.xunit.xml', '*.junit.xml', '*.nosetests.xml')
    logger = logging.getLogger('xunit')

    def process(self, fp, artifact):
        test_list = self.get_tests(fp)

        manager = TestResultManager(self.step, artifact)
        manager.save(test_list)

        return test_list

    @statsreporter.timer('xunithandler_get_test_suites')
    def get_test_suites(self, fp):
        try:
            start = fp.tell()
            try:
                return XunitDelegate(self.step).parse(fp)
            except expat.ExpatError as e:
                if e.message == expat.errors.XML_ERROR_UNKNOWN_ENCODING:
                    # If the encoding is not known, assume it's UTF-8
                    fp.seek(start)
                    return XunitDelegate(self.step, 'UTF-8').parse(fp)
                else:
                    raise e
        except Exception as e:
            uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
            self.logger.warning('Failed to parse XML; (step=%s, build=%s); exception %s',
                                self.step.id.hex, uri, e.message, exc_info=True)
            self.report_malformed()
            return []

    @statsreporter.timer('xunithandler_aggregate_tests_from_suites')
    def aggregate_tests_from_suites(self, test_suites):
        tests = []
        for suite in test_suites:
            tests += suite.test_results

        # avoid deduplicating twice
        if len(test_suites) > 1:
            return _deduplicate_testresults(tests)
        else:
            return tests

    @statsreporter.timer('xunithandler_get_tests')
    def get_tests(self, fp):
        suites = self.get_test_suites(fp)
        return self.aggregate_tests_from_suites(suites)


class XunitDelegate(DelegateParser):
    """
    Main delegating class to parse Xunit files: decides on the appropriate parser depending on the first tag
    """

    def __init__(self, step, encoding=None):
        super(XunitDelegate, self).__init__()
        self.step = step

        self._encoding = encoding
        self._parser = expat.ParserCreate(encoding)
        # Buffer the text so that we call CharacterDataHandler only once (or so) per text field
        # Buffer size was determined from memory limits of machines and testing on a 20MB junit.xml file
        self._parser.buffer_text = True
        self._parser.buffer_size = 10 * 1000 * 1000
        self._parser.XmlDeclHandler = self.xml_decl
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
        return self._subparser.test_suites

    def xml_decl(self, version, encoding, standalone):
        if self._encoding:
            encoding = self._encoding
        if encoding is not None and encoding.upper() == 'UTF8':
            # This encoding isn't supported (it should be 'UTF-8'), and breaks the parser
            raise expat.ExpatError(expat.errors.XML_ERROR_UNKNOWN_ENCODING)

    def _start(self, tag, attrs):
        if tag == 'unittest-results':
            raise ArtifactParseError('Bitten is not supported.')
        else:
            self._set_subparser(XunitParser(self.step, self._parser))
            statsreporter.stats().incr('new_xunit_result_file')
        self._parser.StartElementHandler(tag, attrs)


class XunitBaseParser(object):
    """
    Base class for Xunit parsers
    """
    logger = logging.getLogger('xunit')

    def __init__(self, step, parser):
        self.step = step
        self._parser = parser

        self.test_suites = []
        self._current_result = None

        self._is_message = False
        self._message_start = None
        self._message_tag = None

    def start_message(self, tag, attrs):
        self._is_message = True
        self._message_tag = tag
        self._message_start = None
        # Byte indices are inaccurate if we buffer text
        self._parser.buffer_text = False

    def process_message(self, data):
        if self._message_start is None:
            self._message_start = self._parser.CurrentByteIndex
            self._parser.buffer_text = True

    def close_message(self):
        if self._message_start is not None:
            message_length = self._parser.CurrentByteIndex - self._message_start
            self._current_result.message_offsets.append((self._message_tag, self._message_start, message_length))

        self._parser.buffer_text = True
        self._is_message = False
        self._message_tag = None
        self._message_start = None


class XunitParser(XunitBaseParser):

    def __init__(self, step, parser):
        super(XunitParser, self).__init__(step, parser)
        self._test_is_quarantined = None

    def start(self, tag, attrs):
        # Spec: http://windyroad.com.au/dl/Open%20Source/JUnit.xsd
        if tag == 'testsuites':
            pass
        elif tag == 'testsuite':
            if attrs.get('time'):
                duration_ms = float(attrs['time']) * 1000
            else:
                duration_ms = None
            suite = TestSuite(step=self.step, name=attrs.get('name', None), duration=duration_ms)
            self.test_suites.append(suite)

            # try to assign a result. We will override this if this test suite
            # has tests
            if 'failures' in attrs and int(attrs['failures']) > 0:
                suite.result = Result.failed
            elif 'errors' in attrs and int(attrs['errors']) > 0:
                suite.result = Result.failed
            else:
                # TODO(naphat) what about 'skipped'? we don't have enough information
                # to distinguish between skipped and passing
                suite.result = Result.passed
        elif tag == 'testcase':
            # If there's a previous failure in addition to stdout or stderr,
            # prioritize showing the previous failure because that's what's
            # useful for debugging flakiness.
            message_limit = current_app.config.get('TEST_MESSAGE_MAX_LEN')
            message = truncate_message(attrs.get('last_failure_output'), message_limit) or None

            # Results are found in children elements
            result = Result.unknown

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
            if self._current_result.result == Result.unknown:
                # Only look at the first message
                if tag == 'skipped':
                    self._current_result.result = Result.skipped
                elif tag == 'failure':
                    self._current_result.result = Result.failed
                elif tag == 'error':
                    self._current_result.result = Result.failed
                else:
                    self._current_result.result = Result.passed

            self.start_message(tag, attrs)

    def data(self, data):
        if self._is_message:
            self.process_message(data)

    def end(self, tag):
        if self._is_message:
            self.close_message()
        if tag == 'testsuites':
            pass
        elif tag == 'testsuite':
            self.test_suites[-1].test_results = _deduplicate_testresults(self.test_suites[-1].test_results)
            if self.test_suites[-1].duration is None:
                # NOTE: it is inaccurate to just sum up the duration of individual
                # tests, because tests may be run in parallel
                self.logger.warning('Test suite does not have timing information; (step=%s, build=%s)',
                                    self.step.id.hex, self.step.job.build_id.hex)

            if len(self.test_suites[-1].test_results) > 0:
                self.test_suites[-1].result = aggregate_result([t.result for t in self.test_suites[-1].test_results])

                if self.test_suites[-1].date_created is None:
                    self.test_suites[-1].date_created = min([t.date_created for t in self.test_suites[-1].test_results])
        elif tag == 'testcase':
            if self._current_result.result == Result.unknown:
                # Default result is passing
                self._current_result.result = Result.passed
            if self._test_is_quarantined:
                if self._current_result.result == Result.passed:
                    self._current_result.result = Result.quarantined_passed
                elif self._current_result.result == Result.failed:
                    self._current_result.result = Result.quarantined_failed
                elif self._current_result.result == Result.skipped:
                    self._current_result.result = Result.quarantined_skipped
            self._test_is_quarantined = None
            self.test_suites[-1].test_results.append(self._current_result)
            self._current_result = None
        elif tag == 'test-artifacts':
            pass
        elif tag == 'artifact':
            pass


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
            if e.message and r.message:
                e.message += '\n\n' + r.message
            elif not e.message:
                e.message = r.message or ''
            e.reruns = _careful(max, e.reruns, r.reruns)
            e.artifacts = _careful(add, e.artifacts, r.artifacts)
            e.message_offsets = _careful(add, e.message_offsets, r.message_offsets)
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


def truncate_message(msg, limit):
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


def get_testcase_messages(testcase):
    message = testcase.message or ''
    message_limit = current_app.config.get('TEST_MESSAGE_MAX_LEN')
    # Sort messages by start offset to ensure original ordering
    testcase.messages.sort(key=lambda x: (x.artifact_id, x.start_offset))
    for m in testcase.messages:
        if message:
            message += '\n\n'
        message += \
            (' ' + m.label + ' ').center(78, '=') + '\n' + \
            truncate_message(
                saxutils.unescape(m.get_message().decode('utf-8'), {"&apos;": "'", "&quot;": '"'}),
                message_limit,
            )
    return message
