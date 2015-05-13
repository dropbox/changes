from flask import current_app

from changes.queue.task import tracked_task
from changes.utils.imports import import_string


class SuspiciousOperation(Exception):
    pass


@tracked_task
def fire_signal(signal, kwargs):
    """
    Tasks fire signals by spawning fire_signal tasks; they grab every
    associated listener and spawn run_event_listener tasks for each
    """
    for listener, l_signal in current_app.config['EVENT_LISTENERS']:
        if l_signal == signal:
            run_event_listener.delay(
                listener=listener,
                signal=signal,
                kwargs=kwargs,
            )


@tracked_task
def run_event_listener(listener, signal, kwargs):
    """
    Actually run the listener

    See fire_signal, which doesn't actually run it
    """
    # simple check to make sure this is registered
    if not any(l == listener for l, _ in current_app.config['EVENT_LISTENERS']):
        raise SuspiciousOperation('%s is not a registered event listener' % (listener,))

    func = import_string(listener)
    func(**kwargs)
