#!/usr/bin/python
#
# Copyright 2021 Human Dataware Lab. Co. Ltd.
#
import json
import os
from typing import List, Tuple

from pydtk.db import V4DBHandler as DBHandler
import requests

from .helpers import escape_string


def get_secret_columns(database_id: str) -> List[str]:
    """Returns secret columns in the database.

    Args:
        database_id (str): Escaped database_id

    Returns:
        isecret_columns (List[str])

    """
    # Get config for database
    handler = DBHandler(
        db_class='meta',
        database_id=database_id,
        orient='path',
        read_on_init=False
    )
    config = handler.config

    # Get list of secret columns
    secret_columns = []
    if 'columns' in config.keys():
        for column in config['columns']:
            if 'is_secret' in column.keys() and column['is_secret'] is True:
                secret_columns.append(column['name'])
    return secret_columns


class CheckPermissionClient:
    """Client for checking permission via api-permission-manager."""
    # Get api host
    API_PERMISSION_MANAGER_SERVICE_HOST = os.environ.get('API_PERMISSION_MANAGER_SERVICE_HOST')
    API_PERMISSION_MANAGER_SERVICE_PORT = os.environ.get('API_PERMISSION_MANAGER_SERVICE_PORT')
    if API_PERMISSION_MANAGER_SERVICE_HOST and API_PERMISSION_MANAGER_SERVICE_PORT:
        PERMISSION_MANAGER_SERVICE = f'http://{API_PERMISSION_MANAGER_SERVICE_HOST}:{API_PERMISSION_MANAGER_SERVICE_PORT}'
    else:
        PERMISSION_MANAGER_SERVICE = 'https://demo.dataware-tools.com/api/latest/permission_manager'

    def __init__(self, auth_header: str):
        """Initialize.
        Args:
            auth_header (str)
        """
        self.auth_header = auth_header

    def is_permitted(self, action_id: str, database_id: str) -> bool:
        """Check whether the action is permitted for the user on the database.
        Args:
            action_id (str): ID of an action to check permission.
            database_id (str): ID of an database to check permission.
        Returns:
            (bool): Whether if permitted or not.
        """
        try:
            res = requests.get(
                f'{self.PERMISSION_MANAGER_SERVICE}/permitted-actions/{action_id}',
                params={
                    'database_id': database_id,
                },
                headers={
                    'authorization': self.auth_header,
                },
            )
            res.raise_for_status()
            is_permitted = json.loads(res.text)
            return is_permitted
        except Exception:
            return False

    def columns_to_filter(self, database_id: str):
        """Get columns to filter for public only read users.
        Args:
            database_id (str)
        Returns:
            columns_to_filter (List[str])
        """
        if self.is_permitted('metadata:read', database_id):
            # Can read all
            columns_to_filter = []
        else:
            # Can read only public metadata
            columns_to_filter = get_secret_columns(database_id)
        return columns_to_filter

    def check_permissions(self, action_id: str, database_id: str):
        """Check whether the action is permitted for the user on the database and raise if not.
        Args:
            action_id (str): ID of an action to check permission.
            database_id (str): ID of an database to check permission.
        """
        if not self.is_permitted(action_id, escape_string(database_id, kind='id')):
            raise PermissionError(
                f'Action "{action_id}" is not allowed on database "{database_id}"'
            )

    def filter_permitted_databases(self, database_ids: List[str]) -> Tuple[List[str], List[int]]:
        """Return ids of permitted databases filtered from input database_ids.
        Args:
            database_ids (List[str])
        Returns:
            (List[str]): List of permitted databases.
            (List[int]): Indices of permitted databases in the input list.
        """
        try:
            response = requests.get(
                f'{self.PERMISSION_MANAGER_SERVICE}/permitted-databases',
                headers={
                    'authorization': self.auth_header,
                },
                json={
                    'database_ids': database_ids,
                },
            )
            response.raise_for_status()
            response_data = json.loads(response.text)
            return response_data['database_ids'], response_data['selected_indices']
        except Exception:
            return [], []


class DummyCheckPermissionClient(CheckPermissionClient):
    """Dummy object of CheckPermissionClient (for debugging and testing)."""

    def is_permitted(self, *args, **kwargs) -> bool:
        """Allow all."""
        return True

    def filter_permitted_databases(self, database_ids: List[str]) -> Tuple[List[str], List[int]]:
        """Allow all."""
        return database_ids, list(range(len(database_ids)))
