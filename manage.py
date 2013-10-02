#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()

from changes.db import psyco_gevent
psyco_gevent.make_psycopg_green()


def run_gevent_server(app):
    def action(host=('h', '0.0.0.0'), port=('p', 7777)):
        """run application use gevent http server
        """
        from gevent import pywsgi
        pywsgi.WSGIServer((host, port), app).serve_forever()
    return action


def run_worker(app):
    def action(queues=('queues', 'default')):
        import gevent

        from changes.config import queue

        print 'New worker consuming from queues: %s' % (queues,)

        queues = [q.strip() for q in queues.split(' ') if q.strip()]

        while True:
            with app.app_context():
                try:
                    # Creates a worker that handle jobs in ``default`` queue.
                    worker = queue.get_worker(*queues)
                    worker.work()
                except Exception:
                    import traceback
                    traceback.print_exc()

            gevent.sleep(5)
    return action


from flask.ext.actions import Manager

from changes.config import create_app


app = create_app()

manager = Manager(app)
manager.add_action('run_gevent', run_gevent_server)
manager.add_action('worker', run_worker)

if __name__ == "__main__":
    manager.run()
