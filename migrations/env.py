from __future__ import with_statement
from alembic import context
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

import sqlalchemy as sa
from changes.db.types.enum import Enum
from changes.db.types.filestorage import FileStorage
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
sa.Enum = Enum
sa.FileStorage = FileStorage
sa.GUID = GUID
sa.JSONEncodedDict = JSONEncodedDict

# add your model's MetaData object here
# for 'autogenerate' support
from flask import current_app
from changes.config import create_app, db

import warnings
from sqlalchemy.exc import SAWarning
warnings.simplefilter("ignore", SAWarning)

if not current_app:
    app = create_app()
else:
    app = current_app
app.app_context().push()
target_metadata = db.metadata

# force registration of models
import changes.models  # NOQA


def run_migrations():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connection = db.engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

run_migrations()
