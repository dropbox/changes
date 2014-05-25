from __future__ import absolute_import, division

from collections import defaultdict
from hashlib import md5
from lxml import etree
from sqlalchemy.exc import IntegrityError

from changes.config import db, redis
from changes.models.filecoverage import FileCoverage
from changes.utils.diff_parser import DiffParser

from .base import ArtifactHandler


class CoverageHandler(ArtifactHandler):
    def process(self, fp):
        results = self.get_coverage(fp)

        for result in results:
            try:
                with db.session.begin_nested():
                    db.session.add(result)
            except IntegrityError:
                lock_key = 'coverage:{job_id}:{file_hash}'.format(
                    job_id=result.job_id.hex,
                    file_hash=md5(result.filename.encode('utf-8')).hexdigest(),
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

        cov_data = []
        for lineno in range(max(len(existing.data), len(new.data))):
            try:
                old_cov = existing.data[lineno]
            except IndexError:
                pass

            try:
                new_cov = new.data[lineno]
            except IndexError:
                pass

            if old_cov == 'C' or new_cov == 'C':
                cov_data.append('C')
            elif old_cov == 'U' or new_cov == 'U':
                cov_data.append('U')
            else:
                cov_data.append('N')

        existing.data = ''.join(cov_data)

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
        parsed_diff = diff_parser.parse()

        for file_diff in parsed_diff:
            for diff_chunk in file_diff['chunks']:
                if not file_diff['new_filename']:
                    continue

                lines_by_file[file_diff['new_filename'][2:]].update(
                    d['new_lineno'] for d in diff_chunk if d['action'] in ('add', 'del')
                )
        return lines_by_file

    def get_processed_diff(self):
        if not hasattr(self, '_processed_diff'):
            self._processed_diff = self.process_diff()
        return self._processed_diff

    def add_file_stats(self, result):
        diff_lines = self.get_processed_diff()[result.filename]

        lines_covered = 0
        lines_uncovered = 0
        diff_lines_covered = 0
        diff_lines_uncovered = 0

        for lineno, code in enumerate(result.data):
            # lineno is 1-based in diff
            line_in_diff = bool((lineno + 1) in diff_lines)
            if code == 'C':
                lines_covered += 1
                if line_in_diff:
                    diff_lines_covered += 1
            elif code == 'U':
                lines_uncovered += 1
                if line_in_diff:
                    diff_lines_uncovered += 1

        result.lines_covered = lines_covered
        result.lines_uncovered = lines_uncovered
        result.diff_lines_covered = diff_lines_covered
        result.diff_lines_uncovered = diff_lines_uncovered

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
        step = self.step
        job = self.step.job

        root = etree.parse(fp)

        results = []
        for node in root.iter('class'):
            filename = node.get('filename')
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
