#!/usr/bin/env python


def test_get_catalog():
    """Test `get_catalog` function."""
    from dataware_tools_api_helper import get_catalogs
    catalog = get_catalogs()
    print(catalog)
    assert 'api' in catalog.keys()
    assert 'app' in catalog.keys()


if __name__ == '__main__':
    test_get_catalog()
