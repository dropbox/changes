#!/bin/bash -ex
sudo apt-get install -y build-essential python-setuptools redis-server postgresql libpq-dev libevent-dev libxml2-dev libxslt-dev libffi-dev

npm --version

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

# Tell Changes we don't need the citools puppet again.
if [ ! -z $CHANGES ]; then
    touch /home/ubuntu/SKIP_CITOOLS_PUPPET
fi
