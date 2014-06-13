from __future__ import absolute_import, division, print_function

import os
import os.path
import re
from subprocess import Popen, PIPE

from changes.constants import PROJECT_ROOT
from changes.db.utils import create_or_update, get_or_create
from changes.models import Author, Revision


class CommandError(Exception):
    def __init__(self, cmd, retcode, stdout=None, stderr=None):
        self.cmd = cmd
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr

    def __unicode__(self):
        return '%s returned %d:\nSTDOUT: %r\nSTDERR: %r' % (
            self.cmd, self.retcode, self.stdout, self.stderr)


class BufferParser(object):
    def __init__(self, fp, delim):
        self.fp = fp
        self.delim = delim

    def __iter__(self):
        chunk_buffer = []
        for chunk in self.fp:
            while chunk.find(self.delim) != -1:
                d_pos = chunk.find(self.delim)

                chunk_buffer.append(chunk[:d_pos])

                yield ''.join(chunk_buffer)
                chunk_buffer = []

                chunk = chunk[d_pos + 1:]

            if chunk:
                chunk_buffer.append(chunk)

        if chunk_buffer:
            yield ''.join(chunk_buffer)


class Vcs(object):
    ssh_connect_path = os.path.join(PROJECT_ROOT, 'bin', 'ssh-connect')

    def __init__(self, path, url, username=None):
        self.path = path
        self.url = url
        self.username = username

        self._path_exists = None

    def get_default_env(self):
        return {}

    def run(self, *args, **kwargs):
        if self.exists():
            kwargs.setdefault('cwd', self.path)

        env = os.environ.copy()

        for key, value in self.get_default_env().iteritems():
            env.setdefault(key, value)

        env.setdefault('CHANGES_SSH_REPO', self.url)

        for key, value in kwargs.pop('env', {}):
            env[key] = value

        kwargs['env'] = env
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

        proc = Popen(*args, **kwargs)
        (stdout, stderr) = proc.communicate()
        if proc.returncode != 0:
            raise CommandError(args[0], proc.returncode, stdout, stderr)
        return stdout

    def exists(self):
        return os.path.exists(self.path)

    def clone(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def log(self, parent=None, limit=100):
        raise NotImplementedError

    def export(self, id):
        raise NotImplementedError

    def get_revision(self, id):
        """
        Return a ``Revision`` given by ``id`.
        """
        return self.log(parent=id, limit=1).next()

    def get_default_revision(self):
        raise NotImplementedError


class RevisionResult(object):
    parents = None
    branches = None

    def __init__(self, id, message, author, author_date, committer=None,
                 committer_date=None, parents=None, branches=None):
        self.id = id
        self.message = message
        self.author = author
        self.author_date = author_date
        self.committer = committer or author
        self.committer_date = committer_date or author_date
        if parents is not None:
            self.parents = parents
        if branches is not None:
            self.branches = branches

    def __repr__(self):
        return '<%s: id=%r author=%r subject=%r>' % (
            type(self).__name__, self.id, self.author, self.subject)

    def _get_author(self, value):
        match = re.match(r'^(.+) <([^>]+)>$', value)
        if not match:
            if '@' in value:
                name, email = value, value
            else:
                name, email = value, '{0}@localhost'.format(value)
        else:
            name, email = match.group(1), match.group(2)

        author, _ = get_or_create(Author, where={
            'email': email,
        }, defaults={
            'name': name,
        })

        return author

    @property
    def subject(self):
        return self.message.splitlines()[0]

    def save(self, repository):
        author = self._get_author(self.author)
        if self.author == self.committer:
            committer = author
        else:
            committer = self._get_author(self.committer)

        revision, created = create_or_update(Revision, where={
            'repository': repository,
            'sha': self.id,
        }, values={
            'author': author,
            'committer': committer,
            'message': self.message,
            'parents': self.parents,
            'branches': self.branches,
            'date_created': self.author_date,
            'date_committed': self.committer_date,
        })

        return (revision, created)
