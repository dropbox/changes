from __future__ import absolute_import, division, print_function

from datetime import datetime
from urlparse import urlparse

from changes.utils.cache import memoize
from changes.utils.http import build_uri

from .base import (
    Vcs, RevisionResult, BufferParser, ConcurrentUpdateError, CommandError,
    ContentReadError, UnknownChildRevision, UnknownParentRevision, UnknownRevision,
)

import re
from time import time

LOG_FORMAT = '%H\x01%an <%ae>\x01%at\x01%cn <%ce>\x01%ct\x01%P\x01%B\x02'

ORIGIN_PREFIX = 'remotes/origin/'

BASH_CLONE_STEP = """
#!/bin/bash -eux

REMOTE_URL=%(remote_url)s
LOCAL_PATH=%(local_path)s
REVISION=%(revision)s

BASE_NAME=$(basename "$LOCAL_PATH")
CACHE_PATH="%(cache_dir)s/$BASE_NAME.git"

if [ -d "$CACHE_PATH" ]; then
    echo "Using local repository cache."
    REMOTE_URL="$CACHE_PATH"
fi

if [ ! -d $LOCAL_PATH/.git ]; then
    GIT_SSH_COMMAND="ssh -v" \
    git clone $REMOTE_URL $LOCAL_PATH || \
    git clone $REMOTE_URL $LOCAL_PATH
    pushd $LOCAL_PATH
else
    pushd $LOCAL_PATH
    git remote set-url origin $REMOTE_URL
    GIT_SSH_COMMAND="ssh -v" \
    git fetch --all -p || \
    GIT_SSH_COMMAND="ssh -v" \
    git fetch --all -p
fi

GIT_SSH_COMMAND="ssh -v" \
git fetch origin +refs/*:refs/remotes-all-refs/origin/* || \
GIT_SSH_COMMAND="ssh -v" \
git fetch origin +refs/*:refs/remotes-all-refs/origin/*

%(pre_reset_command)s

%(clean_command)s

if ! git reset --hard $REVISION ; then
    echo "Failed to update to $REVISION"
    exit 1
fi
""".strip()

BASH_PATCH_STEP = """
#!/bin/bash -eux

LOCAL_PATH=%(local_path)s
PATCH_URL=%(patch_url)s

pushd $LOCAL_PATH
PATCH_PATH=/tmp/$(mktemp patch.XXXXXXXXXX)
curl -o $PATCH_PATH $PATCH_URL
git apply --index $PATCH_PATH
export GIT_COMMITTER_NAME="Patch applier" GIT_COMMITTER_EMAIL="dev-tools+git-patch@dropbox.com"
export GIT_AUTHOR_NAME=$GIT_COMMITTER_NAME GIT_AUTHOR_EMAIL=$GIT_COMMITTER_EMAIL
git commit -m 'Diff build'
""".strip()


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

    # This is static so that the repository serializer can easily use it
    @staticmethod
    def get_default_revision():
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

    def branches_for_commit(self, _id):
        return self.get_known_branches(commit_id=_id)

    def get_known_branches(self, commit_id=None):
        """ List all branches or those related to the commit for this repo.

        Either gets all the branches (if the commit_id is not specified) or then
        the branches related to the given commit reference.

        :param commit_id: A commit ID for fetching all related branches. If not
            specified, returns all branch names for this repository.
        :return: List of branches for the commit, or all branches for the repo.
        """
        start_time = time()

        results = []
        command_parameters = ['branch', '-a']
        if commit_id:
            command_parameters.extend(['--contains', commit_id])
        output = self.run(command_parameters)

        for result in output.splitlines():
            # HACK(dcramer): is there a better way around removing the prefix?
            result = result[2:].strip()
            if result.startswith(ORIGIN_PREFIX):
                result = result[len(ORIGIN_PREFIX):]
            if result == 'HEAD':
                continue
            results.append(result)
        self.log_timing('get_known_branches', start_time)
        return list(set(results))

    def run(self, cmd, **kwargs):
        cmd = [self.binary_path] + cmd
        try:
            return super(GitVcs, self).run(cmd, **kwargs)
        except CommandError as e:
            if 'unknown revision or path' in e.stderr:
                raise UnknownRevision(
                    cmd=e.cmd,
                    retcode=e.retcode,
                    stdout=e.stdout,
                    stderr=e.stderr,
                )
            raise

    def clone(self):
        self.run(['clone', '--mirror', self.remote_url, self.path])

    def update(self):
        self.run(['remote', 'set-url', 'origin', self.remote_url])
        try:
            self.run(['fetch', '--all', '-p'])
        except CommandError as e:
            if 'error: cannot lock ref' in e.stderr.lower():
                raise ConcurrentUpdateError(
                    cmd=e.cmd,
                    retcode=e.retcode,
                    stdout=e.stdout,
                    stderr=e.stderr
                )
            raise e

    def log(self, parent=None, branch=None, author=None, offset=0, limit=100,
            paths=None, first_parent=True):
        """ Gets the commit log for the repository.

        Each revision returned includes all the branches with which this commit
        is associated. There will always be at least one associated branch.

        See documentation for the base for general information on this function.
        """
        start_time = time()

        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--pretty=format:%s' % (LOG_FORMAT,)]

        if not first_parent:
            # --date-order can be vastly slower. When --first-parent is
            # provided, the history returned is inherently linear, so
            # there's no freedom to reorder commits at all, meaning
            # --date-order would be effectively a no-op.
            cmd.append('--date-order')
        if first_parent:
            cmd.append('--first-parent')
        if author:
            cmd.append('--author=%s' % (author,))
        if offset:
            cmd.append('--skip=%d' % (offset,))
        if limit:
            cmd.append('--max-count=%d' % (limit,))

        if parent and branch:
            raise ValueError('Both parent and branch cannot be set')
        if branch:
            cmd.append(branch)

        # TODO(dcramer): determine correct way to paginate results in git as
        # combining --all with --parent causes issues
        elif not parent:
            cmd.append('--all')
        if parent:
            cmd.append(parent)

        if paths:
            cmd.append("--")
            cmd.extend([p.strip() for p in paths])

        try:
            result = self.run(cmd)
        except CommandError as cmd_error:
            err_msg = cmd_error.stderr
            if branch and branch in err_msg:
                import traceback
                import logging
                msg = traceback.format_exception(CommandError, cmd_error, None)
                logging.warning(msg)
                raise ValueError('Unable to fetch commit log for branch "{0}".'
                                 .format(branch))
            raise

        self.log_timing('log', start_time)

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
        """Get the textual diff for a revision.
        Args:
            id (str): The id of the revision.
        Returns:
            A string with the text of the diff for the revision.
        Raises:
            UnknownRevision: If the revision wasn't found.
        """
        cmd = ['diff', '%s^..%s' % (id, id)]
        result = self.run(cmd)
        return result

    def get_changed_files(self, id):
        """Returns the list of files changed in a revision.
        Args:
            id (str): The id of the revision.
        Returns:
            A set of filenames
        Raises:
            UnknownRevision: If the revision wan't found.
        """
        cmd = ['diff', '--name-only', '%s^..%s' % (id, id)]
        output = self.run(cmd)
        return set([x.strip() for x in output.splitlines()])

    def is_child_parent(self, child_in_question, parent_in_question):
        cmd = ['merge-base', '--is-ancestor', parent_in_question, child_in_question]
        try:
            self.run(cmd)
            return True
        except CommandError as e:
            expected_err = "fatal: Not a valid commit name "
            m = re.match(r'^\s*fatal: Not a valid commit name (?P<sha>\S+)\s*$', e.stderr)
            if e.retcode == 1:
                return False
            elif e.retcode == 128 and m:
                sha = m.group('sha')
                if sha == parent_in_question:
                    raise UnknownParentRevision(
                        cmd=e.cmd,
                        retcode=e.retcode,
                        stdout=e.stdout,
                        stderr=e.stderr)
                elif sha == child_in_question:
                    raise UnknownChildRevision(
                        cmd=e.cmd,
                        retcode=e.retcode,
                        stdout=e.stdout,
                        stderr=e.stderr)
            else:
                raise

    def get_buildstep_clone(self, source, workspace, clean=True, cache_dir=None, pre_reset_command=None):
        reset_commands = {
            'status': 'git status',
            'checkout': 'git checkout -q master',
            'reset_master': 'git reset master',
        }
        pre_reset = reset_commands.get(pre_reset_command)
        return BASH_CLONE_STEP % dict(
            remote_url=self.remote_url,
            local_path=workspace,
            revision=source.revision_sha,
            cache_dir=cache_dir or "/dev/null",
            clean_command='git clean -fdx' if clean else '',
            pre_reset_command=pre_reset or ''
        )

    def get_buildstep_patch(self, source, workspace):
        return BASH_PATCH_STEP % dict(
            local_path=workspace,
            patch_url=build_uri('/api/0/patches/{0}/?raw=1'.format(
                                source.patch_id.hex)),
        )

    def read_file(self, sha, file_path, diff=None):
        """Read the content of a file at a given revision.

        Args:
            sha (str): the sha identifying the revision
            file_path (str): the path to the file from the root of the repo
            diff (str): the optional patch to apply before reading the config
        Returns:
            str - the content of the file
        Raises:
            CommandError - if the git invocation fails.
            ContentReadError - if the content can't be read because the named file is missing,
                links to something outside the tree, links to an absent file, or links to itself.
        """
        cmd = ['cat-file', '--batch', '--follow-symlinks']
        obj_key = '{revision}:{file_path}'.format(revision=sha, file_path=file_path)
        content = self.run(cmd, input=obj_key)
        info, content = content.split('\n', 1)
        if info.endswith('missing'):
            raise ContentReadError('No such file at revision: {}'.format(obj_key))
        if any(info.startswith(s) for s in ('symlink', 'dangling', 'loop')):
            raise ContentReadError('Unable to read file contents: {}'.format(info.split()[0]))
        if not re.match(r'^[a-f0-9]+ blob \d+$', info):
            raise ContentReadError('Unrecognized metadata for {}: {!r}'.format(obj_key, info))
        assert content.endswith('\n')
        content = content[:-1]
        if diff is None:
            return content

        return self._selectively_apply_diff(file_path, content, diff)
