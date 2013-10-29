from __future__ import absolute_import


def patch_gevent():
    from gevent import monkey
    monkey.patch_all()

    from changes.db import psyco_gevent
    psyco_gevent.make_psycopg_green()
