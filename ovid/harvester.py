# -*- coding: utf-8 -*-
"""
    harvester.py
    ~~~~~~~~~~~~

    Basic OAI-PMH harvesting utilities.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import urllib2
from urllib import urlencode

def request_oai(base_url, verb, **kw):
    """Perform request to base_url with verb and kw args. Return file like."""
    params = kw
    params['verb'] = verb
    url = base_url + urlencode(params)
    return urllib2.urlopen(url)