#!/usr/bin/env python

import tornado.ioloop

from buildbox.app import application

if __name__ == "__main__":
    application.listen(7777)
    tornado.ioloop.IOLoop.instance().start()
