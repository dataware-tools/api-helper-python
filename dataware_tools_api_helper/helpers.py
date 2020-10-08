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

import base64
import json
from flask import session
from flask import _request_ctx_stack as stack
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context
import os
import urllib.request

DEFAULT_API_CATALOG = 'https://raw.githubusercontent.com/dataware-tools/catalog/master/api.json'
DEFAULT_APP_CATALOG = 'https://raw.githubusercontent.com/dataware-tools/catalog/master/app.json'

# A note on distributed tracing:
#
# Although Istio proxies are able to automatically send spans, they need some
# hints to tie together the entire trace. Applications need to propagate the
# appropriate HTTP headers so that when the proxies send span information, the
# spans can be correlated correctly into a single trace.
#
# To do this, an application needs to collect and propagate the following
# headers from the incoming request to any outgoing requests:
#
# x-request-id
# x-b3-traceid
# x-b3-spanid
# x-b3-parentspanid
# x-b3-sampled
# x-b3-flags
#
# This example code uses OpenTracing (http://opentracing.io/) to propagate
# the 'b3' (zipkin) headers. Using OpenTracing for this is not a requirement.
# Using OpenTracing allows you to add application-specific tracing later on,
# but you can just manually forward the headers if you prefer.
#
# The OpenTracing example here is very basic. It only forwards headers. It is
# intended as a reference to help people get started, eg how to create spans,
# extract/inject context, etc.

# A very basic OpenTracing tracer (with null reporter)
tracer = Tracer(
    one_span_per_rpc=True,
    service_name='auth',
    reporter=NullReporter(),
    sampler=ConstSampler(decision=True),
    extra_codecs={Format.HTTP_HEADERS: B3Codec()}
)


def trace():
    """Function decorator that creates opentracing span from incoming b3 headers."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            request = stack.top.request
            try:
                # Create a new span context, reading in values (traceid,
                # spanid, etc) from the incoming x-b3-*** headers.
                span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
                # Note: this tag means that the span will *not* be
                # a child span. It will use the incoming traceid and
                # spanid. We do this to propagate the headers verbatim.
                rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
                span = tracer.start_span(
                    operation_name='op', child_of=span_ctx, tags=rpc_tag
                )
            except Exception as e:
                # We failed to create a context, possibly due to no
                # incoming x-b3-*** headers. Start a fresh span.
                # Note: This is a fallback only, and will create fresh headers,
                # not propagate headers.
                span = tracer.start_span('op')
            with span_in_context(span):
                g = f.__globals__  # use f.func_globals for py < 2.6
                sentinel = object()

                oldvalue = g.get('request', sentinel)
                g['request'] = request

                try:
                    r = f(*args, **kwargs)
                finally:
                    if oldvalue is sentinel:
                        del g['request']
                    else:
                        g['request'] = oldvalue

                return r
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


def get_forward_headers(request):
    headers = {}

    # x-b3-*** headers can be populated using the opentracing span
    span = get_current_span()
    carrier = {}
    tracer.inject(
        span_context=span.context,
        format=Format.HTTP_HEADERS,
        carrier=carrier)

    headers.update(carrier)

    if 'access_token' in session:
        headers['Authorization'] = 'Bearer ' + session['access_token']

    # We handle other (non x-b3-***) headers manually
    if 'user' in session:
        headers['end-user'] = session['user']

    incoming_headers = ['x-request-id']

    for ihdr in incoming_headers:
        val = request.headers.get(ihdr)
        if val is not None:
            headers[ihdr] = val
            # print "incoming: "+ihdr+":"+val

    return headers


def get_jwt_payload_from_request(request: any):
    """Get JWT payload.
    Args:
        request: request object

    Returns:
        (dict): payload in JWT

    """
    user_info = {}
    access_token = request.headers.get('Authorization', ' ').split(' ')[1]
    if len(access_token) > 0:
        b64_string = access_token.split('.')[1]
        b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        user_info = json.loads(base64.b64decode(b64_string))
    return user_info


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
