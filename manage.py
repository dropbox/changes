#!/usr/bin/env python
from gevent import monkey
from buildbox.db import psyco_gevent

monkey.patch_all()
psyco_gevent.make_psycopg_green()


def run_gevent_server(app):
    def action(host=('h', '127.0.0.1'), port=('p', 5000)):
        """run application use gevent http server
        """
        from gevent import wsgi
        wsgi.WSGIServer((host, port), app).serve_forever()
    return action


from flask.ext.actions import Manager

from buildbox.config import create_app


app = create_app()

manager = Manager(app)
manager.add_action('runserver', run_gevent_server)

if __name__ == "__main__":
    manager.run()
