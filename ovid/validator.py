# -*- coding: utf-8 -*-
"""
    validator.py
    ~~~~~~~~~~~~

    The core module of ovid.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import sys
import os

import random
import urllib2
from urllib2 import URLError, HTTPError

from lxml import etree
from lxml.etree import XMLSyntaxError
from lxml.etree import DocumentInvalid

from harvester import request_oai
from ovid import DATA_PATH

OAI_NAMESPACE = "http://www.openarchives.org/OAI/2.0/"
OAI = '{%s}' % OAI_NAMESPACE

DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
DC = '{%s}' % DC_NAMESPACE


class Validator(object):
    """Validate OAI-OMH interfaces"""
    def __init__(self, base_url):
        super(Validator, self).__init__()
        if base_url.endswith('?'):
            self.base_url = base_url
        else:
            self.base_url = base_url + '?'

    def interface_reachable(self):
        """Check if the OAI-PMH interface is working"""
        try:
            res = urllib2.urlopen(self.base_url)
            return res.code
        except URLError, m:
            return str(m)
        except ValueError, m:
            return str(m)
        except HTTPError, e:
            return e.code
    
    
    def check_XML(self, verb):
        """Check if XML response for OAI-PMH verb is well-formed"""
        if verb == 'Identify':
            try:
                remote = request_oai(self.base_url, verb)
                etree.parse(remote)
                return True
            except XMLSyntaxError, message:
                return message
        elif verb == 'ListRecords':
            try:
                remote = request_oai(self.base_url, verb, metadataPrefix='oai_dc')
                etree.parse(remote)
                return True
            except XMLSyntaxError, message:
                return message
            
            
    def validate_XML(self, verb):
        """Check if XML returned for OAI-PMH verb is valid"""
        if verb == 'Identify':
            try:
                remote = request_oai(self.base_url, verb)
                tree = etree.parse(remote)
            except XMLSyntaxError, message:
                return message

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

    def reasonable_batch_size(self, verb, min_batch_size=50, max_batch_size=200):
        """
        Check if a reasonable number of data records is returned for a
        ListRecords/ListIdentifiers request. Return a tuple of
        (result, actual batch size). Result can be -1 (to small), 1 (too
        large) or 0 (reasonable size).
        """
        if verb == 'ListRecords':
            element = 'record'
        if verb == 'ListIdentifiers':
            element = 'header'
        remote = request_oai(self.base_url, verb, metadataPrefix='oai_dc')
        tree = etree.parse(remote)
        records = tree.findall('.//' + OAI + element)
        batch_size = len(records)
        if batch_size < min_batch_size:
            return (-1, batch_size, min_batch_size)
        elif batch_size > max_batch_size:
            return (1, batch_size, max_batch_size)
        else:
            return (0, batch_size)
    
    def incremental_harvesting(self):
        """Check if server supports incremental harvesting by date."""
        remote = request_oai(self.base_url, 'ListRecords', metadataPrefix='oai_dc')
        tree = etree.parse(remote)
        records = tree.findall('.//' + OAI + 'record')
        reference_record = random.sample(records, 1)[0]
        reference_datestamp = reference_record.find('.//' + OAI + 'datestamp').text
        reference_oai_id = reference_record.find('.//' + OAI + 'identifier').text
        
        remote = request_oai(self.base_url, 'ListRecords', 
                            metadataPrefix='oai_dc', _from=reference_datestamp, 
                            until=reference_datestamp)
        tree = etree.parse(remote)                    
        records = tree.findall('.//' + OAI + 'record')
        if len(records) > 1:
            return False
        test_record = records[0]
        test_oai_id = test_record.find('.//' + OAI + 'identifier').text
        if test_oai_id == reference_oai_id:
            return True
        else:
            return False

        