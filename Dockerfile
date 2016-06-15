# Docker is a fast & lightweight container-based virtualization framework.
#
# General info:
#   http://docker.io/
#
# Dockerfile reference:
#   http://docs.docker.io/reference/builder/
#
# Quickstart:
#
#   # Build the image
#   docker build -t my_changes .
#
#   # Create a new container called "changes" using the image built above
#   docker run -d --name=changes -p 127.0.0.1:5000:5000 my_changes

# Ubuntu 14.04, with a proper init(8) for docker.
# https://phusion.github.io/baseimage-docker
FROM phusion/baseimage:0.9.10

# Put your name here if you volunteer to maintain this. :)
#MAINTAINER nobody

# Before installing postgrsql, make sure the we're in a UTF-8 locale.
RUN update-locale --reset LANG=en_US.UTF-8 LANGUAGE=en_US:en

# System-wide dependencies
#RUN echo 'Acquire::http::Proxy { "http://172.17.42.1:3142"; };' > /etc/apt/apt.conf.d/install-apt-proxy
RUN apt-get -qy update
RUN apt-get -qy install \
        python-all python-all-dev python-pip python-virtualenv python-tox \
        python3-all python3-all-dev python3-pip \
        libxml2-dev libev-dev libxslt1-dev nodejs npm postgresql libpq-dev \
        redis-server git mercurial supervisor && \
    apt-get -qy upgrade && \
    ln -s /usr/bin/nodejs /usr/local/bin/node && \
    npm install -g bower
#RUN rm -f /etc/apt/apt.conf.d/install-apt-proxy

# Wipe out any SSH host keys that may have been installed
RUN rm -f /etc/ssh/ssh_host_*key*

# Early configuration (custom configuration should happen after the image is built)
ENV CHANGES_CONF /etc/changes/config.py
ADD docs/examples/changes.conf.py /etc/changes/config.py

# Clone the repo
RUN git clone -q https://github.com/dropbox/changes /srv/changes

## Clone the repo more quickly using a copy of the local repo
## NOTE: There could be privacy implications of shipping this in a public
## image, so we delete it after we're done.
#ADD .git /tmp/changes.git
#RUN git clone -q --reference /tmp/changes.git https://github.com/dropbox/changes /srv/changes
#
# Detach and remove the local repo copy
#RUN cd /srv/changes && \
#    git repack -a && \
#    rm -f .git/objects/info/alternates && \
#    git gc --aggressive --prune=all && \
#    rm -rf /tmp/changes.git

# Create user
RUN adduser --gecos '' --disabled-password changes && \
    /etc/init.d/postgresql start && \
    su postgres -c "createuser --createdb changes" && \
    /etc/init.d/postgresql stop

# Install application dependencies
RUN chown -R changes:changes /srv/changes && \
    su changes -c '\
        cd /srv/changes && \
        virtualenv env && \
        . env/bin/activate && \
        make install-requirements install-test-requirements'

# Check out a more recent copy of the sources
# XXX - remove this once pushed; this really hurts performance
#ADD .git /tmp/changes.git
#RUN \
#    cd /srv/changes && \
#    git fetch /tmp/changes.git && \
#    git checkout -b dev-hack FETCH_HEAD && \
#    git repack -a && \
#    git gc --aggressive --prune=all && \
#    rm -rf /tmp/changes.git

# XXX - another hack -- adopt our Makefile changes without the docker/docker.mk stuff
# TODO remove this once pushed
#ADD Makefile /srv/changes/Makefile
#RUN mkdir /srv/changes/docker && touch /srv/changes/docker/docker.mk

# Populate the database and generate static assets
# TODO Replace 'createdb -E utf-8 changes' with 'make createdb' once the Makefile lands
RUN /etc/init.d/postgresql start && \
    su changes -c 'cd /srv/changes && . env/bin/activate && createdb -E utf-8 changes && make upgrade' && \
    /etc/init.d/postgresql stop

# Add a few more helper scripts & config files
ADD docker/supervisord.conf /etc/supervisor/conf.d/changes.conf
ADD docker/supervisor-run /etc/service/supervisor/run

# Configure openssh server
# - HostKey algorithms:
#   - rsa -- 2048-bit & used for compatibility
#   - ed25519 -- used for speed & resistance to timing attacks
#   - no dsa -- 1024-bit & showing signs of age
#   - no ecdsa -- curve might not be secure (NIST secp256r1) and not particularly fast
# - Authentication: publickey only
# - Don't delay login with reverse DNS lookups
# - Get authorized_keys from the environment.
RUN \
    sed -E -i~ -e '/^(PasswordAuthentication|ChallengeResponseAuthentication|PermitRootLogin|UseDNS|HostKey|AuthorizedKeysFile)\b/s/^/#/' /etc/ssh/sshd_config && \
    echo >>/etc/ssh/sshd_config 'HostKey /etc/ssh/ssh_host_rsa_key' && \
    echo >>/etc/ssh/sshd_config 'HostKey /etc/ssh/ssh_host_ed25519_key' && \
    echo >>/etc/ssh/sshd_config 'PermitRootLogin without-password' && \
    echo >>/etc/ssh/sshd_config 'PasswordAuthentication no' && \
    echo >>/etc/ssh/sshd_config 'ChallengeResponseAuthentication no' && \
    echo >>/etc/ssh/sshd_config 'UseDNS no' && \
    echo >>/etc/ssh/sshd_config 'AuthorizedKeysFile /etc/ssh/authorized_keys/%u /etc/ssh/authorized_keys.env.d/%u .ssh/authorized_keys .ssh/authorized_keys2'

# Configure stuff from the container environment
ADD docker/10_changes_conf_from_env.py /etc/my_init.d/10_changes_conf_from_env.py

# Sanity check
RUN \
    if ls -l /etc/ssh/ssh_host_*key* >/dev/null 2>&1 ; then \
        echo >&2 "There should be no SSH host keys on this machine, found:" ; \
        ls -l /etc/ssh/ssh_host_*key* >&2 ; \
        exit 1; \
    fi

# Default environment
ENV WEB_BASE_URI http://localhost:5000
ENV INTERNAL_BASE_URI http://localhost:5000
ENV SERVER_NAME localhost:5000

# Expose SSH & HTTP ports.  http://localhost:5000
EXPOSE 22
EXPOSE 5000

# Export volumes
#VOLUME /srv/changes
#VOLUME /var/lib/postgresql
#VOLUME /var/lib/redis

# Default invocation
CMD ["/sbin/my_init"]
