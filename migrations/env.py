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
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
sa.Enum = Enum
sa.GUID = GUID
sa.JSONEncodedDict = JSONEncodedDict

# add your model's MetaData object here
# for 'autogenerate' support
from flask import current_app
from changes.config import create_app, db
if not current_app:
    app = create_app()
else:
    app = current_app
app.app_context().push()
target_metadata = db.metadata

# force registration of models
import changes.models  # NOQA


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(engine=db.engine)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
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

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
