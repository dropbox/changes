#!/bin/bash -eux
sudo apt-get install -y build-essential python-setuptools redis-server postgresql libpq-dev libevent-dev libxml2-dev libxslt-dev

npm --version

sudo npm install -g bower
sudo easy_install -U pip
sudo easy_install virtualenv


virtualenv `pwd`/env
sudo -u postgres createuser -s `whoami` --no-password || true
sudo -u postgres createdb changes || true
sudo chown -R `whoami` `npm config get cache`
PATH=`pwd`/env/bin:$PATH make install-test-requirements
