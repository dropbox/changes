"""
This file acts as a default entry point for app creation.
"""

from changes.config import create_app, queue

app = create_app()

# HACK(dcramer): this allows Celery to detect itself -.-
celery = queue.celery
