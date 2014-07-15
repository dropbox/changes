from __future__ import absolute_import, division, print_function

from datetime import datetime
from urlparse import urlparse

from changes.utils.cache import memoize

from .base import Vcs, RevisionResult, BufferParser, CommandError

LOG_FORMAT = '%H\x01%an <%ae>\x01%at\x01%cn <%ce>\x01%ct\x01%P\x01%B\x02'

ORIGIN_PREFIX = 'remotes/origin/'


class LazyGitRevisionResult(RevisionResult):
    def __init__(self, vcs, *args, **kwargs):
        self.vcs = vcs
        super(LazyGitRevisionResult, self).__init__(*args, **kwargs)

    @memoize
    def branches(self):
        return self.vcs.branches_for_commit(self.id)


class GitVcs(Vcs):
    binary_path = 'git'

    def get_default_env(self):
        return {
            'GIT_SSH': self.ssh_connect_path,
        }

    def get_default_revision(self):
        return 'master'

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
        results = []
        output = self.run(['branch', '-a', '--contains', id])
        for result in output.splitlines():
            # HACK(dcramer): is there a better way around removing the prefix?
            result = result[2:].strip()
            if result.startswith(ORIGIN_PREFIX):
                result = result[len(ORIGIN_PREFIX):]
            if result == 'HEAD':
                continue
            results.append(result)
        return list(set(results))

    def run(self, cmd, **kwargs):
        cmd = [self.binary_path] + cmd
        return super(GitVcs, self).run(cmd, **kwargs)

    def clone(self):
        self.run(['clone', '--mirror', self.remote_url, self.path])

    def update(self):
        self.run(['fetch', '--all'])

    def log(self, parent=None, offset=0, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--all', '--pretty=format:%s' % (LOG_FORMAT,)]
        if parent:
            cmd.append(parent)
        if offset:
            cmd.append('--skip=%d' % (offset,))
        if limit:
            cmd.append('--max-count=%d' % (limit,))
        result = self.run(cmd)

        for chunk in BufferParser(result, '\x02'):
            (sha, author, author_date, committer, committer_date,
             parents, message) = chunk.split('\x01')

            # sha may have a trailing newline due to git log adding it
            sha = sha.lstrip('\n')

            parents = filter(bool, parents.split(' '))

            author_date = datetime.utcfromtimestamp(float(author_date))
            committer_date = datetime.utcfromtimestamp(float(committer_date))

            yield LazyGitRevisionResult(
                vcs=self,
                id=sha,
                author=author,
                committer=committer,
                author_date=author_date,
                committer_date=committer_date,
                parents=parents,
                message=message,
            )

    def export(self, id):
        cmd = ['log', '-n 1', '-p', '--pretty="%b"', id]
        result = self.run(cmd)[4:]
        return result

    def is_child_parent(self, child_in_question, parent_in_question):
        cmd = ['merge-base', '--is-ancestor', parent_in_question, child_in_question]
        try:
            self.run(cmd)
            return True
        except CommandError:
            return False
