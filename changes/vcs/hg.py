from __future__ import absolute_import, division, print_function

from datetime import datetime
from email.utils import parsedate_tz, mktime_tz
from urllib.parse import urlparse

from .base import Vcs, RevisionResult, BufferParser

LOG_FORMAT = '{node}\x01{author}\x01{date|rfc822date}\x01{p1node} {p2node}\x01{branches}\x01{desc}\x02'


class MercurialVcs(Vcs):
    binary_path = 'hg'

    def get_default_env(self):
        return {
            'HGPLAIN': '1',
        }

    @property
    def remote_url(self):
        if self.url.startswith(('ssh:', 'http:', 'https:')):
            parsed = urlparse(self.url)
            url = '%s://%s@%s/%s' % (
                parsed.scheme,
                parsed.username or self.username or 'hg',
                parsed.hostname + (':%s' % (parsed.port,) if parsed.port else ''),
                parsed.path.lstrip('/'),
            )
        else:
            url = self.url
        return url

    def run(self, cmd, **kwargs):
        cmd = [
            self.binary_path,
            '--config',
            'ui.ssh={0}'.format(self.ssh_connect_path)
        ] + cmd
        return super(MercurialVcs, self).run(cmd, **kwargs)

    def clone(self):
        self.run(['clone', '--uncompressed', self.remote_url, self.path])

    def update(self):
        self.run(['pull'])

    def log(self, parent=None, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--template=%s' % (LOG_FORMAT,)]
        if parent:
            cmd.append('-r reverse(ancestors(%s))' % (parent,))
        if limit:
            cmd.append('--limit=%d' % (limit,))
        result = self.run(cmd)

        for chunk in BufferParser(result, '\x02'):
            (sha, author, author_date, parents, branches, message) = chunk.split('\x01')

            branches = [b for b in branches.split(' ') if b] or ['default']
            parents = [p for p in parents.split(' ') if p and p != '0' * 40]

            author_date = datetime.utcfromtimestamp(
                mktime_tz(parsedate_tz(author_date)))

            yield RevisionResult(
                id=sha,
                author=author,
                author_date=author_date,
                message=message,
                parents=parents,
                branches=branches,
            )

    def export(self, id):
        cmd = ['diff', '-g', '-c %s' % (id,)]
        result = self.run(cmd)
        return result
