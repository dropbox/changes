from __future__ import absolute_import, division, print_function

from datetime import datetime
from urlparse import urlparse

from .base import Vcs, RevisionResult, BufferParser


LOG_FORMAT = '%H\x01%an <%ae>\x01%at\x01%cn <%ce>\x01%ct\x01%P\x01%B\x02'


class GitVcs(Vcs):
    binary_path = 'git'

    def get_default_env(self):
        return {
            'GIT_SSH': self.ssh_connect_path,
        }

    @property
    def remote_url(self):
        if self.url.startswith(('ssh:', 'http:', 'https:')):
            parsed = urlparse(self.url)
            url = '%s://%s@%s/%s' % (
                parsed.scheme,
                parsed.username or self.username or 'git',
                parsed.hostname + (':%s' % (parsed.port,) if parsed.port else ''),
                parsed.path.lstrip('/'),
            )
        else:
            url = self.url
        return url

    def branches_for_commit(self, id):
        results = self.run(['branch', '--contains', id])
        return [r[2:].strip() for r in results.splitlines()]

    def run(self, cmd, **kwargs):
        cmd = [self.binary_path] + cmd
        return super(GitVcs, self).run(cmd, **kwargs)

    def clone(self):
        self.run(['clone', '--mirror', self.remote_url, self.path])

    def update(self):
        self.run(['fetch', '--all'])
        self.run(['remote', 'prune', 'origin'])
        self.run(['reset', '--hard', 'origin/master'])

    def log(self, parent=None, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--pretty=format:%s' % (LOG_FORMAT,)]
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
                branches=self.branches_for_commit(sha),
                message=message,
            )

    def export(self, id):
        cmd = ['log', '-n 1', '-p', '--pretty="%b"', id]
        result = self.run(cmd)[4:]
        return result
