#!/usr/bin/python
#
# Copyright 2021 Human Dataware Lab. Co. Ltd.
#

import base64
import json
import os
import re
import urllib.request

from deprecated import deprecated
from flask import session

DEFAULT_API_CATALOG = 'https://raw.githubusercontent.com/dataware-tools/catalog/master/api.json'
DEFAULT_APP_CATALOG = 'https://raw.githubusercontent.com/dataware-tools/catalog/master/app.json'


def get_forward_headers(request):
    headers = {}

    if 'access_token' in session:
        headers['Authorization'] = 'Bearer ' + session['access_token']

    if 'user' in session:
        headers['end-user'] = session['user']

    incoming_headers = ['x-request-id']

    for ihdr in incoming_headers:
        val = request.headers.get(ihdr)
        if val is not None:
            headers[ihdr] = val

    return headers


def get_jwt_payload_from_request(request: any):
    """Get JWT payload.
    Args:
        request: request object

    Returns:
        (dict): payload in JWT

    """
    if isinstance(request, dict):
        try:
            authorization = request['headers']['Authorization']
        except (KeyError, IndexError):
            authorization = ''
    else:
        authorization = request.headers.get('Authorization', ' ')
    return get_jwt_payload_from_authorization(authorization)


def get_jwt_payload_from_authorization(authorization: str):
    """Get JWT payload from 'Authorization' value in request headers.

    Args:
        authorization (str): authorization value

    Returns:
        (dict): payload in JWT

    """
    try:
        access_token = authorization.split(' ')[1]
    except (KeyError, IndexError):
        access_token = ''
    return decode_access_token(access_token)


def decode_access_token(access_token: str):
    """Decode JWT token.

    Args:
        access_token (str): token

    Returns:
        (dict): payload in JWT

    """
    user_info = {}
    if len(access_token) > 0:
        b64_string = access_token.split('.')[1]
        b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        user_info = json.loads(base64.b64decode(b64_string))
    return user_info


def escape_string(data: str, kind: str = None):
    """Escape string

    Args:
        data (str or None): input string
        kind (str): 'filtering', 'id'

    Returns:
        (str or None): escaped string

    """
    if data is None:
        return data

    escaped = data

    japanese_ranges = {
        'hiragana': '\u3041-\u309F',
        'katakana': '\u30A1-\u30FF',
        'katakana_hankaku': '\uFF66-\uFF9F',
        'kanji': '\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF',
        'kigou': '\u3000-\u303F',
    }
    japanese_range = ''.join(japanese_ranges.values())

    if kind is None:
        escaped = re.sub(f'[^a-zA-Z0-9{japanese_range}:;.,_=<>" /~!@#$%^&()+-]', '', escaped)
    elif kind == 'filtering':
        escaped = re.sub(f'[^a-zA-Z0-9{japanese_range}:;.,_=<>" /~!@#$%^&()+-]', '', escaped)
    elif kind == 'id':
        escaped = re.sub('[^a-zA-Z0-9_-]', '', escaped)
    elif kind == 'key':
        escaped = re.sub('[^a-zA-Z0-9_=<>/()@-]', '', escaped)
    elif kind == 'path':
        escaped = re.sub(f'[^a-zA-Z0-9{japanese_range}:;.,_=<>/~!@#$%^&()+-]', '', escaped)
    elif kind == 'uuid':
        escaped = re.sub('[^a-zA-Z0-9_-]', '', escaped)
    else:
        pass

    return escaped


@deprecated
def get_catalogs(use_default=False):
    """Get API/APP catalog.

    Args:
        use_default (bool): if True, use the default catalog

    Returns:
        (dict): a dict containing keys `api` and `app`

    """
    def _get(url: str):
        if url.startswith('http'):
            with urllib.request.urlopen(url) as f:
                return json.loads(f.read().decode())
        else:
            with open(url, 'r') as f:
                return json.load(f)

    api_catalog = DEFAULT_API_CATALOG if use_default else os.environ.get('API_CATALOG', DEFAULT_API_CATALOG)
    app_catalog = DEFAULT_APP_CATALOG if use_default else os.environ.get('APP_CATALOG', DEFAULT_APP_CATALOG)

    try:
        return {
            'api': _get(api_catalog),
            'app': _get(app_catalog)
        }
    except IOError:
        return get_catalogs(use_default=True)
    except Exception as e:
        raise e
