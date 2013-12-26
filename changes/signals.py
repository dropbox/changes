from blinker import signal

build_finished = signal('job.finished')


SIGNAL_MAP = {
    'job.finished': build_finished,
}


def register_listener(func, signal_name):
    SIGNAL_MAP[signal_name].connect(func)
