#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

from changes.db import psyco_gevent
psyco_gevent.make_psycopg_green()

from flask.ext.actions import Manager

from changes.config import create_app


app = create_app()

manager = Manager(app)

if __name__ == "__main__":
    manager.run()
