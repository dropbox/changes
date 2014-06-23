#!/bin/bash -ex

echo `whoami`@$HOSTNAME
uname -a

# nothing works without ssh keys, so let's straight up error
# out of theres no keys/agent present
ssh-agent -s
ssh-add -l

REPO_PATH=$WORKSPACE/$CHANGES_PID

if [ -z $REVISION ]; then
  if [ "$REPO_VCS" = "hg" ]; then
    REVISION=default
  else
    REVISION=master
  fi
fi

if [ "$REPO_VCS" = "git" ]; then
  git-clone $REPO_PATH $REPO_URL $REVISION
  git-patch $REPO_PATH $PATCH_URL
else
  hg-clone $REPO_PATH $REPO_URL $REVISION
  hg-patch $REPO_PATH $PATCH_URL
fi

# clean up any artifacts which might be present
for artifact_name in "junit.xml coverage.xml jobs.json tests.json"; do
	find . -name $artifact_name -delete
done

SCRIPT_PATH=/tmp/$(mktemp build-step.XXXXXXXXXX)
echo "$SCRIPT" | tee $SCRIPT_PATH
chmod +x $SCRIPT_PATH

pushd $REPO_PATH

if [ ! -z $WORK_PATH ]; then
    pushd $WORK_PATH
fi

$SCRIPT_PATH
