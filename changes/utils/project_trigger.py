from changes.models import Build
from datetime import datetime, timedelta

import fnmatch
import re


def _compile_patterns(pattern_list):
    return [re.compile(fnmatch.translate(p)) for p in pattern_list]


def _match_file_patterns(patterns, fname):
    return any(pattern.match(fname) for pattern in patterns)


def _in_project_files_whitelist(project_options, files_changed):
    file_whitelist = filter(bool, project_options.get('build.file-whitelist', '').splitlines())
    if file_whitelist:
        whitelist_patterns = _compile_patterns(file_whitelist)
        for filename in files_changed:
            if _match_file_patterns(whitelist_patterns, filename):
                return True
        return False
    return True


def files_changed_should_trigger_project(files_changed, project, project_options, sha, diff=None):
    """Given a list of changed files for a project at a given revision,
    determine if a build should be started.

    Right now, the file blacklist is taken from the in-repo config, while the
    file whitelist is taken from ProjectOption

    Args:
        files_changed (list(str)) - list of changed files
        project (changes.models.Project)
        project_options (dict) - project option with build.file-whitelist loaded
        sha (str) - The sha identifying the revision to look up the config from
        diff (str) - (optional) patch to apply before reading
                     config

    Returns:
        boolean - True if a build should be started.

    Raises:
        InvalidDiffError - When the supplied diff does not apply
        ProjectConfigError - When the config file is in an invalid format.
        NotImplementedError - When the project has no vcs backend
    """
    config_path = project.get_config_path()
    # if config file changed, then we always run the build
    if config_path in files_changed:
        return True

    config = project.get_config(sha, diff, config_path)
    if not _time_based_exclusion_filter(config, project):
        return False

    blacklist = config['build.file-blacklist']

    # filter out files in blacklist
    blacklist_patterns = _compile_patterns(blacklist)
    files_changed = filter(lambda f: not _match_file_patterns(blacklist_patterns, f), files_changed)

    # apply whitelist, if there are still files left
    if len(files_changed) > 0:
        return _in_project_files_whitelist(project_options, files_changed)
    else:
        return False


def _time_based_exclusion_filter(project_options, project):
    mins_between_builds = project_options.get('build.minimum-minutes-between-builds', 0)

    # By default, don't skip anything.
    if not mins_between_builds:
        return True

    # No filtering of build type is done here to keep this simple
    builds_in_last_n_minutes = Build.query.filter(
        Build.project == project,
        Build.date_created >= datetime.now() - timedelta(minutes=mins_between_builds),
    ).count()

    if builds_in_last_n_minutes != 0:
        return False

    return True
