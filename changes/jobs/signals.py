from flask import current_app
from changes.experimental.stats import incr, decr

from changes.queue.task import tracked_task
from changes.utils.imports import import_string


class SuspiciousOperation(Exception):
    pass


@tracked_task
def fire_signal(signal, kwargs):
    incr('fire_signal')
    for listener, l_signal in current_app.config['EVENT_LISTENERS']:
        if l_signal == signal:
            run_event_listener.delay(
                listener=listener,
                signal=signal,
                kwargs=kwargs,
            )
    decr('fire_signal')


@tracked_task
def run_event_listener(listener, signal, kwargs):
    incr('run_event_listener')
    # simple check to make sure this is registered
    if not any(l == listener for l, _ in current_app.config['EVENT_LISTENERS']):
        raise SuspiciousOperation('%s is not a registered event listener' % (listener,))

    func = import_string(listener)
    func(**kwargs)
    decr('run_event_listener')
