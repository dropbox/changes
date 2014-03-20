import logging

from blinker import Signal


class RobustSignal(Signal):
    def __init__(self, name, **kwargs):
        super(RobustSignal, self).__init__(name, **kwargs)
        self.logger = logging.getLogger(name)

    def send_robust(self, *args, **kwargs):
        sender = kwargs.get('sender', None)
        for receiver in self.receivers_for(sender):
            try:
                receiver(*args, **kwargs)
            except Exception as e:
                self.logger.exception(unicode(e))


job_finished = RobustSignal('job.finished')
build_finished = RobustSignal('build.finished')
revision_created = RobustSignal('revision.created')

SIGNAL_MAP = {
    'job.finished': job_finished,
    'build.finished': build_finished,
    'revision.created': revision_created,
}


def register_listener(func, signal_name):
    SIGNAL_MAP[signal_name].connect(func)
