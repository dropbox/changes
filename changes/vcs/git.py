from __future__ import absolute_import, division, print_function

from datetime import datetime

from .base import Vcs, RevisionResult, BufferParser


LOG_FORMAT = '%H\x01%an <%ae>\x01%at\x01%cn <%ce>\x01%ct\x01%P\x01%B\x02'


class GitVcs(Vcs):
    binary_path = 'git'

    def clone(self):
        self.run([self.binary_path, 'clone', self.url, self.path])

    def update(self):
        self.run([self.binary_path, 'fetch', '--all'])
        self.run([self.binary_path, 'remote', 'prune', 'origin'])

    def log(self, parent=None, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = [self.binary_path, 'log', '--pretty=format:%s' % (LOG_FORMAT,)]
        if parent:
            cmd.append(parent)
        if limit:
            cmd.append('-n %d' % (limit,))
        result = self.run(cmd)

        for chunk in BufferParser(result, '\x02'):
            (sha, author, author_date, committer, committer_date,
             parents, message) = chunk.split('\x01')

            # sha may have a trailing newline due to git log adding it
            sha = sha.lstrip('\n')

            parents = filter(bool, parents.split(' '))

            author_date = datetime.utcfromtimestamp(float(author_date))
            committer_date = datetime.utcfromtimestamp(float(committer_date))

            yield RevisionResult(
                id=sha,
                author=author,
                committer=committer,
                author_date=author_date,
                committer_date=committer_date,
                parents=parents,
                message=message,
            )
