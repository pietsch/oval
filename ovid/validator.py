# -*- coding: utf-8 -*-
"""
    validator.py
    ~~~~~~~~~~~~

    The core module of ovid.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import sys
import os

import urllib2
from lxml import etree
from lxml.etree import XMLSyntaxError
from lxml.etree import DocumentInvalid

from harvester import request_oai
from ovid import DATA_PATH

class Validator(object):
    """Knows how to validate OAI-OMH interfaces"""
    def __init__(self, base_url):
        super(Validator, self).__init__()
        self.base_url = base_url

    def interface_reachable(self):
        """Check if the OAI-PMH interface is working"""
        try:
            urllib2.urlopen(self.base_url)
            return True
        except urllib2.HTTPError, e:
            return e.code
    
    
    def check_XML(self, verb):
        """Check if XML response of OAI-PMH verb is well-formed"""
        if verb == 'Identify':
            try:
                remote = request_oai(self.base_url, verb)
                etree.parse(remote)
                return True
            except XMLSyntaxError, message:
                return m
        elif verb == 'ListRecords':
            try:
                remote = request_oai(self.base_url, verb, metadataPrefix='oai_dc')
                etree.parse(remote)
                return True
            except XMLSyntaxError, message:
                return m
            
            
    def validate_XML(self, verb):
        """Check if XML of OAI-PMH verb is valid"""        
        if verb == 'Identify':
            try:
                remote = request_oai(self.base_url, verb)
                tree = etree.parse(remote)
            except XMLSyntaxError, m:
                return m

        elif verb == 'ListRecords':
            try:
                remote = request_oai(self.base_url, verb, metadataPrefix='oai_dc')
                tree = etree.parse(remote)
            except XMLSyntaxError, m:
                return m
        schema_file = os.path.join(DATA_PATH, 'combined.xsd')
        schema_tree = etree.parse(schema_file)
        schema = etree.XMLSchema(schema_tree)
        try:
            schema.assertValid(tree)
            return True
        except DocumentInvalid, message:
            return message
            
        
        