#!/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/bin/supervisord
if [ -f /etc/default/supervisor ] ; then
    . /etc/default/supervisor
fi
DAEMON_OPTS="-c /etc/supervisor/supervisord.conf $DAEMON_OPTS"

exec "$DAEMON" $DAEMON_OPTS --nodaemon
