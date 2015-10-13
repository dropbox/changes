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
        root = etree.fromstring(fp.read())

        if root.tag == 'coverage':
            return self.get_cobertura_coverage(root)
        elif root.tag == 'report':
            return self.get_jacoco_coverage(root)
        raise NotImplementedError('Unsupported coverage format')

    def get_cobertura_coverage(self, root):
        step = self.step
        job = self.step.job

        results = []
        for node in root.iter('class'):
            filename = node.get('filename')
            if not filename:
                self.logger.warn('Unable to determine filename for node: %s', node)
                continue

            file_coverage = []
            for lineset in node.iterchildren('lines'):
                lineno = 0
                for line in lineset.iterchildren('line'):
                    number, hits = int(line.get('number')), int(line.get('hits'))
                    if lineno < number - 1:
                        for lineno in range(lineno, number - 1):
                            file_coverage.append('N')
                    if hits > 0:
                        file_coverage.append('C')
                    else:
                        file_coverage.append('U')
                    lineno = number

            result = FileCoverage(
                step_id=step.id,
                job_id=job.id,
                project_id=job.project_id,
                filename=filename,
                data=''.join(file_coverage),
            )
            self.add_file_stats(result)

            results.append(result)

        return results

    def get_jacoco_coverage(self, root):
        step = self.step
        job = self.step.job

        results = []
        for package in root.iter('package'):
            package_path = 'src/main/java/{}'.format(package.get('name'))
            for sourcefile in package.iter('sourcefile'):
                # node name resembles 'com/example/foo/bar/Resource'
                filename = '{filepath}/{filename}'.format(
                    filepath=package_path,
                    filename=sourcefile.get('name'),
                )

                file_coverage = []
                lineno = 0
                for line in sourcefile.iterchildren('line'):
                    number, hits = int(line.get('nr')), int(line.get('ci'))
                    if lineno < number - 1:
                        for lineno in range(lineno, number - 1):
                            file_coverage.append('N')
                    if hits > 0:
                        file_coverage.append('C')
                    else:
                        file_coverage.append('U')
                    lineno = number

                result = FileCoverage(
                    step_id=step.id,
                    job_id=job.id,
                    project_id=job.project_id,
                    filename=filename,
                    data=''.join(file_coverage),
                )
                self.add_file_stats(result)

                results.append(result)

        return results
