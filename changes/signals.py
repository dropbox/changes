from blinker import signal

job_finished = signal('job.finished')
build_finished = signal('build.finished')


SIGNAL_MAP = {
    'job.finished': job_finished,
    'build.finished': build_finished,
}


def register_listener(func, signal_name):
    SIGNAL_MAP[signal_name].connect(func)
