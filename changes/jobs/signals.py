from flask import current_app

from changes.queue.task import tracked_task
from changes.utils.imports import import_string


class SuspiciousOperation(Exception):
    pass


@tracked_task
def fire_signal(signal, kwargs):
    pass

@tracked_task
def run_event_listener(listener, signal, kwargs):
    pass