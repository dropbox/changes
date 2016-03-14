from __future__ import absolute_import, division

from collections import defaultdict
from hashlib import md5
from lxml import etree
from sqlalchemy.exc import IntegrityError

from changes.config import db, redis
from changes.lib.coverage import merge_coverage, get_coverage_stats
from changes.models.filecoverage import FileCoverage
from changes.utils.diff_parser import DiffParser

from .base import ArtifactHandler


class CoverageHandler(ArtifactHandler):
    FILENAMES = ('coverage.xml', '*.coverage.xml')

    def process(self, fp):
        results = self.get_coverage(fp)

        for result in results:
            try:
                with db.session.begin_nested():
                    db.session.add(result)
            except IntegrityError:
                lock_key = 'coverage:{job_id}:{file_hash}'.format(
                    job_id=result.job_id.hex,
                    file_hash=md5(result.filename).hexdigest(),
                )
                with redis.lock(lock_key):
                    result = self.merge_coverage(result)
                    db.session.add(result)
            db.session.commit()

        return results

    def merge_coverage(self, new):
        existing = FileCoverage.query.filter(
            FileCoverage.job_id == new.job_id,
            FileCoverage.filename == new.filename,
        ).first()

        existing.data = merge_coverage(existing.data, new.data)

        self.add_file_stats(existing)

        return existing

    def process_diff(self):
        lines_by_file = defaultdict(set)
        try:
            source = self.step.job.build.source
        except AttributeError:
            return lines_by_file

        diff = source.generate_diff()

        if not diff:
            return lines_by_file

        diff_parser = DiffParser(diff)
        return diff_parser.get_lines_by_file()

    def get_processed_diff(self):
        if not hasattr(self, '_processed_diff'):
            self._processed_diff = self.process_diff()
        return self._processed_diff

    def add_file_stats(self, result):
        diff_lines = self.get_processed_diff()[result.filename]

        (result.lines_covered,
         result.lines_uncovered,
         result.diff_lines_covered,
         result.diff_lines_uncovered) = get_coverage_stats(diff_lines, result.data)

    def get_coverage(self, fp):
        """
        Return a phabricator-capable coverage mapping.

        >>> {
        >>>     'foo.py': 'NNNUUUUUUUUUUUUCCCUUUUUCCCCCCCCCNNCNCNCCCNNNN',
        >>> }

        Line flags consists of a single character coverage indicator for each line in the file.

        - N: no coverage available
        - U: uncovered
        - C: covered
        """
        try:
            parser = etree.XMLParser(target=CoverageParser(self))
            return etree.parse(fp, parser)
        except etree.XMLSyntaxError as e:
            self.logger.warn(str(e))
            return []


class DelegateParser(object):
    """DelegateParser is a no-op streaming XML parser class intended for
    subclassing.  It allows you to base your final choice of streaming XML
    parser on information from the XML document.  Subclasses should override
    some or all of the `_start`, `_end`, `_data`, and `_close` methods to
    inspect the XML file as its being parsed.  Once the subclass has decided on
    what parser to use, it should call `_set_subparser`. At this point, all
    future parse events will be directed to the subparser, and the `_*` methods
    will no longer be called.  Note that the subparser will begin receiving
    parse events from the point where DelegateParser left off, that is: past
    parse events will *not* be repeated.
    """

    def __init__(self):
        self._subparser = None

    def _set_subparser(self, subparser):
        self._subparser = subparser

    def _start(self, tag, attrib):
        pass

    def _end(self, tag):
        pass

    def _data(self, data):
        pass

    def _close(self):
        return None

    def start(self, tag, attrib):
        if self._subparser:
            self._subparser.start(tag, attrib)
        else:
            self._start(tag, attrib)

    def end(self, tag):
        if self._subparser:
            self._subparser.end(tag)
        else:
            self._end(tag)

    def data(self, data):
        if self._subparser:
            self._subparser.data(data)
        else:
            self._data(data)

    def close(self):
        if self._subparser:
            return self._subparser.close()
        else:
            return self._close()


class CoverageParser(DelegateParser):
    """Parses a Cobertura or Jacoco XML file into a list of FileCoverage objects."""

    def __init__(self, coverage_handler):
        super(CoverageParser, self).__init__()
        self.coverage_handler = coverage_handler

    def _start(self, tag, attrib):
        # check the root tag name to determine which type of coverage file this is
        if tag == 'coverage':
            self._set_subparser(CoberturaCoverageParser(self.coverage_handler))
        elif tag == 'report':
            self._set_subparser(JacocoCoverageParser(self.coverage_handler))
        else:
            # the root tag is not any of the known coverage type
            raise NotImplementedError('Unsupported coverage format')

    def _close(self):
        # because we choose a subparser after seeing the root element, the only
        # way we'll get here is if the document is empty
        raise etree.XMLSyntaxError("Empty file", None, 1, 1)


class CoberturaCoverageParser(object):
    """Parses a Cobertura XML file into a list of FileCoverage objects."""

    def __init__(self, coverage_handler):
        self.coverage_handler = coverage_handler
        self.step = coverage_handler.step
        self.job = coverage_handler.step.job
        self.results = []
        self.in_file = False

    def start(self, tag, attrib):
        if tag == 'class':
            if 'filename' not in attrib:
                self.coverage_handler.logger.warn(
                    'Unable to determine filename for class node with attributes: %s', attrib)
            else:
                self.filename = attrib['filename']
                self.file_coverage = []
                self.current_lineno = 0
                self.in_file = True
        elif tag == 'line':
            if self.in_file:
                number = int(attrib['number'])
                hits = int(attrib['hits'])
                branch = attrib.get('branch') == 'true'
                # the line numbers in the file should be strictly increasing
                assert self.current_lineno < number
                if self.current_lineno < number - 1:
                    for self.current_lineno in range(self.current_lineno, number - 1):
                        self.file_coverage.append('N')

                # count partial branch coverage as uncovered
                if branch:
                    # condition-coverage attrib looks something like '50% (2/4)'
                    if 'condition-coverage' not in attrib:
                        # condition-coverage should always be present if branch="true".  if it's
                        # not, log a warning and mark the line uncovered (to avoid false positives)
                        self.coverage_handler.logger.warn(
                            'Line node with branch="true" has no condition-coverage attribute. ' +
                            'Node attributes: %s', attrib)
                        self.file_coverage.append('U')
                    elif attrib['condition-coverage'].startswith('100%'):
                        self.file_coverage.append('C')
                    else:
                        self.file_coverage.append('U')
                else:
                    if hits > 0:
                        self.file_coverage.append('C')
                    else:
                        self.file_coverage.append('U')
                self.current_lineno = number

    def end(self, tag):
        if tag == 'class':
            if self.in_file:
                result = FileCoverage(
                    step_id=self.step.id,
                    job_id=self.job.id,
                    project_id=self.job.project_id,
                    filename=self.filename,
                    data=''.join(self.file_coverage),
                )
                self.coverage_handler.add_file_stats(result)
                self.results.append(result)

                self.in_file = False

    def data(self, data):
        pass

    def close(self):
        return self.results


class JacocoCoverageParser(object):
    """Parses a Jacoco XML file into a list of FileCoverage objects."""

    def __init__(self, coverage_handler):
        self.coverage_handler = coverage_handler
        self.step = coverage_handler.step
        self.job = coverage_handler.step.job
        self.results = []
        self.in_file = False

    def start(self, tag, attrib):
        if tag == 'package':
            if 'name' not in attrib:
                self.coverage_handler.logger.warn(
                    'Unable to determine name for package node with attributes: %s', attrib)
            else:
                self.package_path = 'src/main/java/{}'.format(attrib['name'])
        elif tag == 'sourcefile':
            if 'name' not in attrib:
                self.coverage_handler.logger.warn(
                    'Unable to determine name for sourcefile node with attributes: %s', attrib)
            else:
                self.filename = '{}/{}'.format(self.package_path, attrib['name'])
                self.file_coverage = []
                self.current_lineno = 0
                self.in_file = True
        elif tag == 'line':
            if self.in_file:
                number = int(attrib['nr'])
                hits = int(attrib['ci'])
                # the line numbers in the file should be strictly increasing
                assert self.current_lineno < number
                if self.current_lineno < number - 1:
                    for self.current_lineno in range(self.current_lineno, number - 1):
                        self.file_coverage.append('N')

                if hits > 0:
                    self.file_coverage.append('C')
                else:
                    self.file_coverage.append('U')
                self.current_lineno = number

    def end(self, tag):
        if tag == 'class':
            if self.in_file:
                result = FileCoverage(
                    step_id=self.step.id,
                    job_id=self.job.id,
                    project_id=self.job.project_id,
                    filename=self.filename,
                    data=''.join(self.file_coverage),
                )
                self.coverage_handler.add_file_stats(result)
                self.results.append(result)

                self.in_file = False

    def data(self, data):
        pass

    def close(self):
        return self.results
