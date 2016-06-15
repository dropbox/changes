#!/usr/bin/env python3

import json
import os
import re
import shutil

def setup_ssh_authorized_keys(env):
    DEST_DIR = "/etc/ssh/authorized_keys.env.d"

    lines_by_user = {}
    for name in env:
        if not name.startswith("authorized_keys:"):
            continue
        try:
            ak, user, n = name.split(":")
            int(n)
        except ValueError:
            continue
        else:
            if ak != "authorized_keys":
                continue

        if user not in lines_by_user:
            lines_by_user[user] = []

        try:
            for line in env[name].split("\n"):
                line = line.rstrip()
                lines_by_user[user].append(line)
        except Exception:
            continue

    # Clear the destination directory
    if os.path.exists(DEST_DIR):
        shutil.rmtree(DEST_DIR)
    os.mkdir(DEST_DIR)

    # Write new keys
    for user, lines in lines_by_user.items():
        with open(os.path.join(DEST_DIR, user), "w") as f:
            for line in lines:
                print(line, file=f)

def update_changes_conf(env):
    replace_vars = ('INTERNAL_BASE_URI', 'WEB_BASE_URI', 'SERVER_NAME', 'REPO_ROOT', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET')
    replace_regexes = tuple(re.compile("^(" + re.escape(n) + ")\s*=") for n in replace_vars)
    conf_filename = env['CHANGES_CONF']
    backup_filename = conf_filename + "~"
    temp_filename = conf_filename + ".tmp"

    # Save a backup
    shutil.copy2(conf_filename, backup_filename)

    # Replace vars and write to temp file
    with open(conf_filename, "r") as infile:
        with open(temp_filename, "w") as outfile:
            shutil.copystat(conf_filename, temp_filename)
            for line in infile:
                line = line.rstrip()
                for r in replace_regexes:
                    m = r.search(line)
                    if m:
                        name = m.group(1)
                        if name in env:
                            line = "{0} = {1!r}".format(name, env[name])
                            break
                print(line, file=outfile)

    # Rename-replace.  Hopefully, this wasn't a symlink.
    os.rename(temp_filename, conf_filename)

def main():
    with open("/etc/container_environment.json", "rb") as f:
        env = json.loads(f.read().decode('utf-8'))

    setup_ssh_authorized_keys(env)
    update_changes_conf(env)

if __name__ == '__main__':
    main()
