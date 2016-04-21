from __future__ import absolute_import, division, print_function

import os
import os.path
import re
import shutil
import tempfile

from subprocess import Popen, PIPE, check_call, CalledProcessError

from changes.constants import PROJECT_ROOT
from changes.db.utils import create_or_update, get_or_create, try_create
from changes.models.author import Author
from changes.models.revision import Revision
from changes.models.source import Source
from changes.config import statsreporter
from changes.utils.diff_parser import DiffParser

from time import time


class CommandError(Exception):
    def __init__(self, cmd, retcode, stdout=None, stderr=None):
        self.cmd = cmd
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr

    def __unicode__(self):
        return '%s returned %d:\nSTDOUT: %r\nSTDERR: %r' % (
            self.cmd, self.retcode, self.stdout, self.stderr)

    def __str__(self):
        return self.__unicode__().encode('utf-8')


class UnknownRevision(CommandError):
    """Indicates that an operation was attempted on a
    revision that doesn't appear to exist."""
    pass


class UnknownChildRevision(UnknownRevision):
    """Indicates that VCS was queried for a parent-child relationship with a
    a child revision that doesn't appear to exist."""
    pass


class UnknownParentRevision(UnknownRevision):
    """Indicates that VCS was queried for a parent-child relationship with a
    a parent revision that doesn't appear to exist."""
    pass


class ConcurrentUpdateError(CommandError):
    """Indicates that a command failed because a vcs update is running."""
    pass


class InvalidDiffError(Exception):
    """This is used when a diff is invalid and fails to apply. It is NOT
    a subclass of CommandError, as it is not a vcs command"""
    pass


class ContentReadError(Exception):
    """Indicates that an attempt to read the contents of a file in the repo failed.
    """
    pass


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
        kwargs['stdin'] = PIPE

        input = kwargs.pop('input', None)

        proc = Popen(*args, close_fds=True, **kwargs)
        (stdout, stderr) = proc.communicate(input=input)
        if proc.returncode != 0:
            raise CommandError(args[0], proc.returncode, stdout, stderr)
        return stdout

    def exists(self):
        return os.path.exists(self.path)

    def clone(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def log(self, parent=None, branch=None, author=None, offset=0, limit=100):
        """ Gets the commit log for the repository.

        Only one of parent or branch can be specified for restricting searches.
        If parent is set, it is used to identify any ancestor revisions,
            regardless of their branch.
        If branch is set, all revisions in the branch AND any ancestor commits
            are returned.

        For any revisions returned, the list of associated branches returned is
        tool specific and may or may not include ancestor branch names. See tool
        implementations for exact behavior of this function.

        :param parent: Parent at which revision search begins.
        :param branch: Branch name the revision must be associated with.
        :param author: The author name or email to filter results.
        :param offset: An offset into the results at which to begin.
        :param limit: The maximum number of results to return.
        :return: A list of revisions matching the given criteria.
        """
        raise NotImplementedError

    def export(self, id):
        """Get the textual diff for a revision.
        Args:
            id (str): The id of the revision.
        Returns:
            A string with the text of the diff for the revision.
        Raises:
            UnknownRevision: If the revision wasn't found.
        """
        raise NotImplementedError

    def get_changed_files(self, id):
        """Returns the list of files changed in a revision.
        Args:
            id (str): The id of the revision.
        Returns:
            A set of filenames
        Raises:
            UnknownRevision: If the revision wan't found.
        """
        diff = self.export(id)
        diff_parser = DiffParser(diff)
        return diff_parser.get_changed_files()

    def get_default_revision(self):
        raise NotImplementedError

    def is_child_parent(self, child_in_question, parent_in_question):
        raise NotImplementedError

    def get_known_branches(self):
        """ This is limited to parallel trees with names.
        :return: A list of unique names for the branches.
        """
        raise NotImplementedError

    # XXX(dcramer): not overly happy with the buildstep commands API
    def get_buildstep_clone(self, source, workspace, clean=True, cache_dir="/dev/null", pre_reset_command=None):
        raise NotImplementedError

    def get_buildstep_patch(self, source, workspace):
        raise NotImplementedError

    def log_timing(self, command, start_time):
        repo_type = 'unknown'
        classname = self.__class__.__name__
        if "Git" in classname:
            repo_type = 'git'
        elif "Mercurial" in classname:
            repo_type = 'hg'

        timer_name = "changes_vcs_perf_{}_command_{}".format(
            repo_type, command)
        time_taken = time() - start_time

        statsreporter.stats().log_timing(timer_name, time_taken * 1000)

    def read_file(self, sha, file_path, diff=None):
        """Read the content of a file at a given revision.

        Args:
            sha (str): the sha identifying the revision
            file_path (str): the path to the file from the root of the repo
            diff (str): the optional patch to apply before reading the config
        Returns:
            str - the content of the file
        Raises:
            CommandError - if the file or the revision cannot be found
        """
        raise NotImplementedError

    def _selectively_apply_diff(self, file_path, file_content, diff):
        """A helper function that takes a diff, extract the parts of the diff
        relating to `file_path`, and apply it to `file_content`.

        If the diff does not involve `file_path`, then `file_content` is
        returned, untouched.

        Args:
            file_path (str) - the path of the file to look for in the diff
            file_content (str) - the content of the file to base on
            diff (str) - diff in unidiff format
        Returns:
            str - `file_content` with the diff applied on top of it
        Raises:
            InvalidDiffError - when the supplied diff is invalid.
        """
        parser = DiffParser(diff)
        selected_diff = None
        for file_dict in parser.parse():
            if file_dict['new_filename'] is not None and file_dict['new_filename'][2:] == file_path:
                selected_diff = parser.reconstruct_file_diff(file_dict)
        if selected_diff is None:
            return file_content
        temp_patch_file_path = None
        temp_dir = None
        try:
            # create a temporary file to house the patch
            fd, temp_patch_file_path = tempfile.mkstemp()
            os.write(fd, selected_diff)
            os.close(fd)

            # create a temporary folder where we will mimic the structure of
            # the repo, with only the config inside it
            dir_name, _ = os.path.split(file_path)
            temp_dir = tempfile.mkdtemp()
            if len(dir_name) > 0:
                os.makedirs(os.path.join(temp_dir, dir_name))
            temp_file_path = os.path.join(temp_dir, file_path)

            with open(temp_file_path, 'w') as f:
                f.write(file_content)

            # apply the patch
            try:
                check_call([
                    'patch',
                    '--strip=1',
                    '--unified',
                    '--directory={}'.format(temp_dir),
                    '--input={}'.format(temp_patch_file_path),
                ])
            except CalledProcessError:
                raise InvalidDiffError
            with open(temp_file_path, 'r') as f:
                patched_content = f.read()

        finally:
            # clean up
            if temp_patch_file_path and os.path.exists(temp_patch_file_path):
                os.remove(temp_patch_file_path)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        return patched_content


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

        # we also want to create a source for this item as it's the canonical
        # representation in the UI
        source = try_create(Source, {
            'revision_sha': self.id,
            'repository': repository,
        })

        return (revision, created, source)
