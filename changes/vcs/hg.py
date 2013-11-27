from __future__ import absolute_import, division, print_function

from datetime import datetime

from .base import Vcs, RevisionResult, BufferParser

LOG_FORMAT = '{node}\x01{author}\x01{date|hgdate}\x01{p1node} {p2node}\x01{desc}\x02'


class MercurialVcs(Vcs):
    binary_path = 'hg'

    def clone(self):
        self.run([self.binary_path, 'clone', '--uncompressed', self.url, self.path])

    def update(self):
        self.run([self.binary_path, 'pull'])

    def log(self, parent=None, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = [self.binary_path, 'log', '--template=%s' % (LOG_FORMAT,)]
        if parent:
            cmd.append('-r %s' % (parent,))
        if limit:
            cmd.append('--limit=%d' % (limit,))
        result = self.run(cmd)

        for chunk in BufferParser(result, '\x02'):
            (sha, author, author_date, parents, message) = chunk.split('\x01')

            parents = filter(lambda x: x and x != '0' * 40, parents.split(' '))

            author_date = datetime.utcfromtimestamp(float(author_date.replace(' ', '.')))

            yield RevisionResult(
                id=sha,
                author=author,
                author_date=author_date,
                message=message,
                parents=parents,
            )
