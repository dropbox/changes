from fnmatch import fnmatch


def in_project_files_whitelist(project_options, files_changed):
    file_whitelist = filter(bool, project_options.get('build.file-whitelist', '').splitlines())
    if file_whitelist:
        for filename in files_changed:
            if any(fnmatch(filename, pattern) for pattern in file_whitelist):
                return True
        return False
    return True
