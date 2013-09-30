#!/usr/bin/env python


def web():
    from gevent import wsgi
    from changes.config import create_app

    print "Listening on http://0.0.0.0:5000"

    app = create_app()
    wsgi.WSGIServer(('0.0.0.0', 5000), app).serve_forever()
