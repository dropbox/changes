"""
This file acts as a default entry point for app creation.
"""

from changes.config import create_app, queue
import sys

# command line parameter allows us to run changes with a profiler
# easier than maintaining two separate app configs
profiler_directory = None
for idx, arg in enumerate(sys.argv):
    if arg == "--run-profiler" and len(sys.argv) > idx + 1:
        profiler_directory = sys.argv[idx + 1]
        break


app = create_app(profiler_directory=profiler_directory)

# HACK(dcramer): this allows Celery to detect itself -.-
celery = queue.celery
