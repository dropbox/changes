#!/bin/bash -ex
sudo apt-get install -y build-essential python-setuptools redis-server postgresql libpq-dev libevent-dev libxml2-dev libxslt-dev

npm --version

sudo npm install -g bower
sudo easy_install -U pip
sudo easy_install virtualenv


redis-server -v
virtualenv ~/env
sudo -u postgres createuser -s `whoami` --no-password || true
sudo -u postgres createdb changes || true
sudo chown -R `whoami` `npm config get cache`
source ~/env/bin/activate
time make install-test-requirements
