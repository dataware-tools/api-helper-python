#!/usr/bin/python
#
# Copyright 2020 Human Dataware Lab. Co. Ltd.
# Copyright 2017 Istio Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import sys
import os

from authlib.integrations.flask_client import OAuth
from flask import Flask, session, redirect
import http.client as http_client
from six.moves.urllib.parse import urlencode

from dataware_tools_api_helper import trace, get_forward_headers

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
http_client.HTTPConnection.debuglevel = 1

app = Flask(__name__)
logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'test'

servicesDomain = "" if (os.environ.get("SERVICES_DOMAIN") is None) else "." + os.environ.get("SERVICES_DOMAIN")

# Authentication
AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL', '')
AUTH0_LOGOUT_URL = os.environ.get('AUTH0_LOGOUT_URL', '')
AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID', '')
AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET', '')
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN', '')
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE', '')

oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)


# The UI:
@app.route('/')
@trace()
def index():
    """Index page."""
    headers = get_forward_headers(request)
    user = session.get('user', '')
    return 'User: {0}'.format(user)


@app.route('/healthz')
def healthz():
    return 'ok'


@app.route('/login')
def login():
    return auth0.authorize_redirect(
        redirect_uri=AUTH0_CALLBACK_URL,
        audience=AUTH0_AUDIENCE
    )


@app.route('/callback')
def callback():
    response = auth0.authorize_access_token()
    session['access_token'] = response['access_token']
    userinfo_response = auth0.get('userinfo')
    userinfo = userinfo_response.json()
    session['user'] = userinfo['nickname']
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': AUTH0_LOGOUT_URL, 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


class Writer(object):
    def __init__(self, filename):
        self.file = open(filename, 'w')

    def write(self, data):
        self.file.write(data)

    def flush(self):
        self.file.flush()


if __name__ == '__main__':
    p = int(os.environ.get('APP_PORT', '8080'))
    print("start at port {}".format(p))
    app.run(host='0.0.0.0', port=p, debug=True, threaded=True)
