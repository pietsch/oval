# -*- coding: utf-8 -*-
"""
    harvester.py
    ~~~~~~~~~~~~
    
    Basic OAI-PMH harvesting utilities.
    
    ### NEW VERSION IMPLEMENTING THE ITERATOR PATTERN ###
    
    
    :copyright: Copyright 2011 Mathias Loesch.
"""

OAI = '{http://www.openarchives.org/OAI/%s/}'

DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
DC = '{%s}' % DC_NAMESPACE


import time
from time import sleep
import hashlib
import pickle
from itertools import chain
import urllib2 
from urllib2 import HTTPError, URLError, Request
from urllib import urlencode
from StringIO import StringIO

from ordereddict import OrderedDict
from oval import __version__ as ovalversion
from lxml import etree

CACHE = OrderedDict()
    
# Caching
def is_obsolete(entry, duration):
    return time.time() - entry['time'] > duration

def compute_key(function, args, kw):
    key = pickle.dumps((function.func_name, args, kw))
    return hashlib.sha1(key).hexdigest()

def memoize(duration=30, max_length=10):
    """Donald Michie's memo function for caching."""
    def _memoize(function):
        def __memoize(*args, **kw):
            key = compute_key(function, args, kw)
            if len(CACHE) > max_length:
                # Pop the oldest item from the cache
                CACHE.popitem(last=False)
            # do we have a response for the request?
            if (key in CACHE and
                not is_obsolete(CACHE[key], duration)):
                return CACHE[key]['value']
            # new request
            result = function(*args, **kw)
            CACHE[key] = {
                            'value': result,
                            'time': time.time()
            }
            return result
        return __memoize
    return _memoize


def normalize_params(params):
    """Clean parameters in accordance with OAI-PMH."""
    if params.get('resumptionToken') is not None:
        #metadataPrefix/from/until not allowed if resumptionToken -> remove
        try:
            del params['metadataPrefix']
        except KeyError:
            pass
        try:
            del params['_from']
        except KeyError:
            pass
        try:
            del params['until']
        except KeyError:
            pass
    # from is a reserved word in Python; use _from instead
    if params.get("_from") is not None:
        params['from'] = params['_from']
        del params['_from']
    nparams = {}
    for param in params:
        if params[param] is not None:
            nparams[param] = params[param]
    return nparams

@memoize()
def fetch_data(base_url, method, params, retries=5):
    """Perform actual request and return the data."""
    data = urlencode(params)
    if method == 'POST':
        request = Request(base_url)
        request.add_data(data)
    elif method == 'GET':
        request = Request(base_url + data)
    request.add_header('User-Agent', 'oval/%s' % ovalversion)
    for i in range(retries):
        try:
            response = urllib2.urlopen(request)
            return response.read()
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
        except Exception:
            raise

def configure_request(base_url, method='POST'):
    """Closure to preconfigure the static request params."""
    def request_oai(**kw):
        """Perform OAI request to base_url. Return parsed response."""
        params = kw
        params = normalize_params(params)
        return etree.XML(fetch_data(base_url, method, params))
    return request_oai

class RecordIter(object):
    """Iterator over OAI records gradually aggregated via OAI-PMH."""
    def __init__(self, base_url, verb, metadataPrefix, _from=None, until=None, 
                deleted=False, protocol_version='2.0', method='POST'):
        self.base_url = base_url
        self.verb = verb
        self.metadataPrefix = metadataPrefix
        self._from = _from
        self.until = until
        self.deleted = deleted # include deleted records?
        self.protocol_version = protocol_version
        self.method = method
        
        #OAI namespace
        self.oai_namespace = OAI % self.protocol_version
        # resumptionToken
        self.token = None
        if self.verb == 'ListRecords':
            self.element = 'record'
        elif self.verb == 'ListIdentifiers':
            self.element = 'header'
        #Configure request method
        self.request_oai = configure_request(self.base_url, self.method)
        #Fetch the initial portion
        response = self.request_oai(verb=self.verb, 
                            metadataPrefix=self.metadataPrefix,
                            _from=self._from, until=self.until)
        self.token = self._get_resumption_token(response)
        self.record_list = self._get_records(response)

    def __iter__(self):
        return self
    
    def _is_not_deleted(self, record):
        if self.element == 'record':
            header = record.find('.//' + self.oai_namespace + 'header')
        elif self.element == 'header':
            header = record # work on header element directly in case of ListId
        if header.attrib.get('status') == 'deleted':
            return False
        else:
            return True
    
    def _get_resumption_token(self, xml_tree):
        token = xml_tree.find('.//' + self.oai_namespace + 'resumptionToken')
        if token is None:
            return None
        else:
            return token.text
    
    def _get_records(self, xml_tree):
        records = xml_tree.findall('.//' + self.oai_namespace + self.element)
        if self.deleted == False:
            records = filter(self._is_not_deleted, records)
        return records
        
    def next(self):
        if (len(self.record_list) == 0 and self.token is None):
            raise StopIteration
        elif len(self.record_list) == 0:
            response = self.request_oai(verb=self.verb, 
                        metadataPrefix=self.metadataPrefix,
                        _from=self._from, until=self.until,
                        resumptionToken=self.token)
            self.record_list = self._get_records(response)
            self.token = self._get_resumption_token(response)
        current_record = self.record_list.pop()
        return current_record