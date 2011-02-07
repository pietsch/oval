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
    """Perform request to base_url with verb and kw args"""
    params = kw
    params['verb'] = verb
    if verb == 'ListRecords':
        url = base_url + urlencode(params)
        return urllib2.urlopen(url)
    if verb == 'Identify':
        url = base_url + urlencode(params)
        return urllib2.urlopen(url)