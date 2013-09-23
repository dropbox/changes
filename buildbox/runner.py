#!/usr/bin/env python


def main():
    import tornado.ioloop

    from buildbox.app import application

    print "Listening on http://0.0.0.0:7777"

    application.listen(7777)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
