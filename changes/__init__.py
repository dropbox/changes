import os
import subprocess

try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('changes').version
except Exception:
    VERSION = 'unknown'


def _get_git_revision_info(checkout_dir):
    try:
        git_command = [
            'git',
            '--work-tree',
            checkout_dir,
            '--git-dir',
            os.path.normpath(os.path.join(checkout_dir, '.git', '')),
            'show',
            '--pretty="%s"' % "%H\x01%ae\x01%ct\x01%s",
            '-s']
        r = subprocess.check_output(git_command, close_fds=True).strip().strip('"')
        (commit_hash, author_email, commit_time, subject) = r.split("\x01")
        return {
            'hash': commit_hash,
            'author_email': author_email,
            'commit_time': commit_time,
            'subject': subject,
        }
    except Exception:
        return None


_cached_revision_info = None


def get_revision_info(use_cache=True):
    """
    NOTE: Results of this function may be cached.
    Returns a dictionary of information about the current revision -
      hash: the commit hash
      author_email: email of the author
      commit_time: commit time of this revision (updated on amend, rebase, etc.)
      subject: the commit subject/title
    Returns None if this info cannot be determined
    """
    global _cached_revision_info
    if use_cache:
        if _cached_revision_info:
            return _cached_revision_info
    package_dir = os.path.dirname(__file__)
    checkout_dir = os.path.normpath(os.path.join(package_dir, os.pardir))
    path = os.path.join(checkout_dir, '.git')
    if os.path.exists(path):
        info = _get_git_revision_info(checkout_dir)
        if use_cache:
            _cached_revision_info = info
        return info
    return None


def get_version():
    base = VERSION
    if __build__:
        base = '%s (%s)' % (base, __build__)
    return base

__buildfacts__ = get_revision_info()
__build__ = __buildfacts__['hash'] if isinstance(__buildfacts__, dict) else None
__docformat__ = 'restructuredtext en'
