from __future__ import absolute_import, division, print_function

from datetime import datetime
from rfc822 import parsedate_tz, mktime_tz
from urlparse import urlparse

from changes.utils.http import build_uri

from .base import Vcs, RevisionResult, BufferParser

LOG_FORMAT = '{node}\x01{author}\x01{date|rfc822date}\x01{p1node} {p2node}\x01{branches}\x01{desc}\x02'

BASH_CLONE_STEP = """
#!/bin/bash -eux

REMOTE_URL=%(remote_url)s
LOCAL_PATH=%(local_path)s
REVISION=%(revision)s

if [ ! -d $LOCAL_PATH/.hg ]; then
    hg clone --uncompressed $REMOTE_URL $LOCAL_PATH
    pushd $LOCAL_PATH
else
    pushd $LOCAL_PATH
    hg recover || true
    hg pull $REMOTE_URL
fi

if ! hg up --clean $REVISION ; then
    echo "Failed to update to $REVISION"
    exit 1
fi

# similar to hg purge, but without requiring the extension
hg status -un0 | xargs -0 rm -rf
""".strip()

BASH_PATCH_STEP = """
#!/bin/bash -eux

LOCAL_PATH=%(local_path)s
PATCH_URL=%(patch_url)s

pushd $LOCAL_PATH
PATCH_PATH=/tmp/$(mktemp patch.XXXXXXXXXX)
curl -o $PATCH_PATH $PATCH_URL
hg import --no-commit $PATCH_PATCH
""".strip()


class MercurialVcs(Vcs):
    binary_path = 'hg'

    def get_default_env(self):
        return {
            'HGPLAIN': '1',
        }

    # This is static so that the repository serializer can easily use it
    @staticmethod
    def get_default_revision():
        return 'default'

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

    def log(self, parent=None, branch=None, author=None, offset=0, limit=100):
        """ Gets the commit log for the repository.

        Each revision returned has exactly one branch name associated with it.
        This is the branch name encoded into the revision changeset description.

        See documentation for the base for general information on this function.
        """
        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--template=%s' % (LOG_FORMAT,)]

        if parent and branch:
            raise ValueError('Both parent and branch cannot be set')

        # Build the -r parameter value into r_str with branch, parent and author
        r_str = None
        if branch:
            r_str = ('branch({1}) or ancestors({1})'.format(r_str, branch))
        if parent:
            r_str = ('ancestors(%s)' % parent)
        if author:
            r_str = ('({r}) and author("{0}")' if r_str else 'author("{0}")')\
                .format(author, r=r_str)
        if r_str:
            cmd.append('-r reverse({0})'.format(r_str))

        if limit:
            cmd.append('--limit=%d' % (offset + limit,))
        result = self.run(cmd)

        for idx, chunk in enumerate(BufferParser(result, '\x02')):
            if idx < offset:
                continue

            (sha, author, author_date, parents, branches, message) = chunk.split('\x01')

            branches = filter(bool, branches.split(' ')) or ['default']
            parents = filter(lambda x: x and x != '0' * 40, parents.split(' '))

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

    def is_child_parent(self, child_in_question, parent_in_question):
        cmd = ['debugancestor', parent_in_question, child_in_question]
        result = self.run(cmd)
        return parent_in_question in result

    def get_known_branches(self):
        """ Gets all the named branches.
        :return: A list of unique names for the branches.
        """
        cmd = ['branches']
        results = self.run(cmd)

        branch_names = set()
        for line in results.splitlines():
            if line:
                name = line.split(None, 1)
                if name[0]:
                    branch_names.add(name[0])

        return list(branch_names)

    def get_buildstep_clone(self, source, workspace):
        return BASH_CLONE_STEP % dict(
            remote_url=self.remote_url,
            local_path=workspace,
            revision=source.revision_sha,
        )

    def get_buildstep_patch(self, source, workspace):
        return BASH_PATCH_STEP % dict(
            local_path=workspace,
            patch_url=build_uri('/api/0/patches/{0}/?raw=1'.format(
                                source.patch_id.hex)),
        )
