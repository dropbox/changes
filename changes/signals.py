from blinker import signal

build_finished = signal('build.finished')


SIGNAL_MAP = {
    'build.finished': build_finished,
}


def register_listener(func, signal_name):
    SIGNAL_MAP[signal_name].connect(func)
