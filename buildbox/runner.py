#!/usr/bin/env python


def web():
    import tornado.ioloop

    from buildbox.app import application

    print "Listening on http://0.0.0.0:7777"

    application.listen(7777)
    tornado.ioloop.IOLoop.instance().start()


def poller():
    import logging
    import time
    import traceback

    from buildbox.poller import Poller

    instance = Poller()
    instance.logger.setLevel(logging.INFO)
    instance.logger.addHandler(logging.StreamHandler())
    while True:
        try:
            instance.run()
        except Exception:
            traceback.print_exc()
            time.sleep(10)
        time.sleep(1)
