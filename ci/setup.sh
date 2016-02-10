#!/bin/bash -ex
sudo apt-get install -y build-essential python-setuptools redis-server postgresql libpq-dev libevent-dev libxml2-dev libxslt-dev libffi-dev nodejs libfontconfig1

# We don't necessarily need a specific version of npm, but this ensures we don't
# use a particularly old one.
NPM_VERSION='>= 3.5.2'
# Only install if we can't list the expected version
npm list -g npm@"$NPM_VERSION" || sudo npm install -g npm@"$NPM_VERSION"


# Install bower only if it's not installed already.
bower help || sudo npm install -g bower
sudo easy_install -U pip
sudo easy_install virtualenv


redis-server -v
virtualenv ~/env
sudo -u postgres createuser -s `whoami` --no-password || true
sudo -u postgres createdb changes || true
sudo chown -R `whoami` `npm config get cache` || true
source ~/env/bin/activate
time make install-test-requirements
