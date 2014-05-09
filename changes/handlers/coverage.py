from __future__ import absolute_import, division

from lxml import etree
from sqlalchemy.exc import IntegrityError

from changes.config import db
from changes.models.filecoverage import FileCoverage

from .base import ArtifactHandler


class CoverageHandler(ArtifactHandler):
    def process(self, fp):
        results = self.get_coverage(fp)

        for result in results:
            try:
                with db.session.begin_nested():
                    db.session.add(result)
            except IntegrityError:
                result = self.merge_coverage(result)

        return results

    def merge_coverage(self, new):
        existing = FileCoverage.query.filter(
            FileCoverage.job_id == new.job_id,
            FileCoverage.filename == new.filename,
        ).first()

        cov_data = []
        for lineno in xrange(max(len(existing.data), len(new.data))):
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

        return existing

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

        root = etree.fromstring(fp.read())

        results = []
        for node in root.iter('class'):
            file_coverage = []
            for lineset in node.iterchildren('lines'):
                lineno = 0
                for line in lineset.iterchildren('line'):
                    number, hits = int(line.get('number')), int(line.get('hits'))
                    if lineno < number - 1:
                        for lineno in xrange(lineno, number - 1):
                            file_coverage.append('N')
                    if hits > 0:
                        file_coverage.append('C')
                    else:
                        file_coverage.append('U')
                    lineno = number
            results.append(FileCoverage(
                step_id=step.id,
                job_id=job.id,
                project_id=job.project_id,
                filename=node.get('filename'),
                data=''.join(file_coverage),
            ))

        return results
