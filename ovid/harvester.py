# -*- coding: utf-8 -*-
"""
    harvester.py
    ~~~~~~~~~~~~

    Basic OAI-PMH harvesting utilities.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import urllib2 
from urllib2 import HTTPError
from urllib import urlencode
from time import sleep

def request_oai(base_url, verb, retries=5,**kw):
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
    for i in range(retries):
        try:
            remote = urllib2.urlopen(url)
            return remote
            break
        except HTTPError, e:
            if e.code == 503:
                try:
                    wait_time = int(e.hdrs.get('Retry-After'))
                except TypeError:
                    wait_time = None
                if wait_time is None:
                    sleep(100)
                else:
                    sleep(wait_time)
            else:
                raise
    