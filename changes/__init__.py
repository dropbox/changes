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
            '--pretty="%s"' % "%H\x01%ae\x01%at\x01%s",
            '-s']
        r = subprocess.check_output(git_command).strip().strip('"')
        (commit_hash, author_email, author_time, subject) = r.split("\x01")
        return {
            'hash': commit_hash,
            'author_email': author_email,
            'author_time': author_time,
            'subject': subject
        }
    except Exception:
        return None


def get_revision_info():
    """
    Returns a dictionary of information about the current revision -
      hash: the commit hash
      author_email: email of the author
      author_time: when was this committed by the author (different than commit_time!)
      subject: the commit subject/title
    Returns None if this info cannot be determined
    """
    package_dir = os.path.dirname(__file__)
    checkout_dir = os.path.normpath(os.path.join(package_dir, os.pardir))
    path = os.path.join(checkout_dir, '.git')
    if os.path.exists(path):
        return _get_git_revision_info(checkout_dir)
    return None


def get_version():
    base = VERSION
    if __build__:
        base = '%s (%s)' % (base, __build__)
    return base

__buildfacts__ = get_revision_info()
__build__ = __buildfacts__['hash'] if isinstance(__buildfacts__, dict) else None
__docformat__ = 'restructuredtext en'
