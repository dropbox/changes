from changes.constants import Cause
from changes.models.build import Build
from changes.models.source import Source

# Known, supported tags with specific and non-overlapping uses that Changes pays attention to.
_KEY_TAGS = {'commit', 'commit-queue', 'test-snapshot', 'snapshot', 'phabricator', 'arc test'}


def is_initial_commit_build(build):
    # type: (Build) -> bool
    """
    A commit build is a build created in response to a permanent repository commit.
    Args:
        build (Build): The build to check.
    Returns:
        bool: Whether the argument appears to be a commit build.
    """
    if not build.source.is_commit():
        return False
    if build.cause == Cause.snapshot:
        return False
    # Ensure we don't have conflicting tags.
    if build.tags and set(build.tags).intersection(_KEY_TAGS - {'commit'}):
        return False
    return build.tags and 'commit' in build.tags


def is_any_commit_build(build):
    # type: (Build) -> bool
    """
    A commit build is a build created in response to a permanent repository commit, OR
    a recreation of such a build (as when retrying to avoid a flake or after an infrastructure fix).
    Args:
        build (Build): The build to check.
    Returns:
        bool: Whether the argument appears to be a commit build.
    """
    if not build.source.is_commit():
        return False
    if build.cause == Cause.snapshot:
        return False
    # Ensure we don't have conflicting tags.
    if build.tags and set(build.tags).intersection(_KEY_TAGS - {'commit'}):
        return False
    return True


def get_any_commit_build_filters():
    """
    Must be used with a query that provides Build joined with Source.
    Returns:
        list: list of query filters to restrict to all builds on commits.

    """
    non_commit_tags = _KEY_TAGS - {'commit'}
    return [
        Build.cause != Cause.snapshot,
        Source.patch_id == None,  # NOQA
    ] + [~Build.tags.any(tag) for tag in non_commit_tags]


def is_arc_test_build(build):
    # type: (Build) -> bool
    """
    An arc test build is a build created by an invocation of `arc test`, or
    a recreation of such a build.
    Args:
        build (Build): The build to check.
    Returns:
        bool: Whether the argument appears to be an arc test build.
    """
    return build.tags and 'arc test' in build.tags


def is_phabricator_diff_build(build):
    # type: (Build) -> bool
    """
    A Phabricator diff build is a build created by Phabricator in response to a revision being
    modified or a recreation of such a build.
    Args:
        build (Build): The build to check.
    Returns:
        bool: Whether the argument appears to be a Phabricator diff build.
    """
    # TODO: Verify 'phabricator' tag?
    target = build.target
    return target and target.startswith(u'D') and not is_arc_test_build(build)
