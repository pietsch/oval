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
    """
        Perform request to base_url with verb and OAI args. Return file like.
        Note that "from" is a reserved word in Python; use "_from" instead.
    """
    params = kw
    params['verb'] = verb
    # from is a reserved word in Python; use _from instead
    if "_from" in params.keys():
        params['from'] = params['_from']
        del params['_from']
    url = base_url + urlencode(params)
    return urllib2.urlopen(url)