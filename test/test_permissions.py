#!/usr/bin/env python


def test_get_secret_columns(setup_database):
    from dataware_tools_api_helper.permissions import get_secret_columns
    assert get_secret_columns('default') == ['secret_column']
