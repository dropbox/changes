from fnmatch import fnmatch


def in_project_files_whitelist(project_options, files_changed):
    file_whitelist = filter(bool, project_options.get('build.file-whitelist', '').splitlines())
    if file_whitelist:
        for filename in files_changed:
            if any(fnmatch(filename, pattern) for pattern in file_whitelist):
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
    """
    config_path = project.get_config_path()
    # if config file changed, then we always run the build
    if config_path in files_changed:
        return True

    config = project.get_config(sha, config_path, diff)
    blacklist = config['build.file-blacklist']

    # filter out files in blacklist
    files_changed = filter(
        lambda f: not any([fnmatch(f, b) for b in blacklist]), files_changed)

    # apply whitelist, if there are still files left
    if len(files_changed) > 0:
        return in_project_files_whitelist(project_options, files_changed)
    else:
        return False
