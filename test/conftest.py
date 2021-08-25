#!/usr/bin/env python
import os

from pydtk.db import V4DBHandler as DBHandler
import pytest


@pytest.fixture()
def setup_database():
    # Remove database if exist
    if os.path.exists('/tmp/api-helper-python/default.json'):
        os.remove('/tmp/api-helper-python/default.json')

    # Set envs
    os.environ['PYDTK_META_DB_ENGINE'] = 'tinymongo'
    os.environ['PYDTK_META_DB_HOST'] = '/tmp/api-helper-python'

    database_id = 'default'

    # Setup DB
    handler = DBHandler(
        db_class='meta',
        database_id=database_id,
        orient='record_id',
        read_on_init=False
    )
    handler.save()

    # Update config
    handler = DBHandler(
        db_class='meta',
        database_id=database_id,
        orient='path',
        read_on_init=False
    )
    config = {k: v for k, v in handler.config.items() if not k.startswith('_')}
    config['columns'].append({
        'name': 'secret_column',
        'dtype': 'string',
        'aggregation': 'first',
        'is_secret': True,
    })
    handler.config.update(config)
    handler.save()
