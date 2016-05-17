#!/bin/bash -ex
sudo apt-get install -y build-essential python-setuptools redis-server postgresql libpq-dev libevent-dev libxml2-dev libxslt-dev libffi-dev nodejs libfontconfig1

# We don't necessarily need a specific version of npm, but this ensures we don't
# use a particularly old one.
NPM_VERSION='>= 3.5.2'
# Only install if we can't list the expected version
npm list -g npm@"$NPM_VERSION" || sudo npm install -g npm@"$NPM_VERSION"


# Install bower only if it's not installed already.
bower help || sudo npm install -g bower
easy_install-2.7 --version
sudo easy_install-2.7 -U pip
sudo easy_install-2.7 virtualenv


redis-server -v
virtualenv ~/env
sudo -u postgres createuser -s `whoami` --no-password || true
sudo -u postgres createdb changes || true
sudo chown -R `whoami` `npm config get cache` || true
# npm keeps running into 'EXDEV' issues when it attempts to rename files across
# "device" boundaries, presumably due to overlay filesystem. This hack-patching
# is ugly and shouldn't be necessary, but it is the most reliable path to a useful build
# right now.
pushd $(npm root -g)/npm \
    && sudo npm install fs-extra \
    && sudo sed -i -e s/graceful-fs/fs-extra/ -e s/fs.rename/fs.move/ ./lib/utils/rename.js
popd
source ~/env/bin/activate
time make install-test-requirements

# Not necessarily required for tests, but we want to make
# sure static JS compilation works, both from scratch and incrementally.
time make static
