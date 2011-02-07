# -*- coding: utf-8 -*-
"""
    validator.py
    ~~~~~~~~~~~~

    The core module of ovid.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import urllib2
from lxml import etree
from lxml.etree import XMLSyntaxError

from harvester import request_oai

class Validator(object):
    """Knows how to validate OAI-OMH interfaces"""
    def __init__(self, base_url):
        super(Validator, self).__init__()
        self.base_url = base_url

    def interface_reachable(self):
        """Check if the OAI-PMH interface is working"""
        try:
            urllib2.urlopen(self.base_url)
            return "OK"
        except urllib2.HTTPError, e:
            return e.code
    
    def wellformed_XML(self, verb):
        """Check if XML response of OAI-PMH verb is well-formed"""
        try:
            remote = request_oai(self.base_url, verb)
            etree.parse(remote)
            return 'OK'
        except XMLSyntaxError, m:
            return m
    
