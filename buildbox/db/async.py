from concurrent.futures import ThreadPoolExecutor
from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor


class AsyncConnectionManager(object):
    def __init__(self, io_loop=None, concurrency=8):
        self.io_loop = io_loop or IOLoop.current()
        self.executor = ThreadPoolExecutor(concurrency)

    @run_on_executor
    def commit(self, session):
        try:
            result = session.commit()
            session.expunge_all()
            return result
        finally:
            session.close()
