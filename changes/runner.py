#!/usr/bin/env python


def web():
    from gevent import wsgi
    from changes.config import create_app

    print "Listening on http://0.0.0.0:5000"

    app = create_app()
    wsgi.WSGIServer(('0.0.0.0', 5000), app).serve_forever()


def poller():
    import logging
    import time
    import traceback

    from changes.config import create_app
    from changes.poller import Poller

    app = create_app()

    instance = Poller(app=app)
    instance.logger.setLevel(logging.INFO)
    instance.logger.addHandler(logging.StreamHandler())
    while True:
        try:
            instance.run()
        except Exception:
            traceback.print_exc()
        time.sleep(30)
