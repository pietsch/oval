# -*- coding: utf-8 -*-
"""
    validator.py
    ~~~~~~~~~~~~

    The core module of ovid.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import os

import random
import urllib2
from urllib2 import URLError, HTTPError
import re

from lxml import etree
from lxml.etree import XMLSyntaxError
from lxml.etree import DocumentInvalid

from ovid.harvester import request_oai
from ovid import DATA_PATH

OAI_NAMESPACE = "http://www.openarchives.org/OAI/2.0/"
OAI = '{%s}' % OAI_NAMESPACE

DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
DC = '{%s}' % DC_NAMESPACE

# Minimal Dublin Core elements according to DRIVER and DINI
MINIMAL_DC_SET = set([
                'identifier',
                'title',
                'date',
                'type',
                'creator'])

# Date scheme according to ISO 8601
DC_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# Helper functions

def get_records(base_url, metadataPrefix='oai_dc'):
    """
    Helper function for getting records. Returns a list of etree elements.
    """
    remote = request_oai(base_url, 'ListRecords', metadataPrefix=metadataPrefix)
    tree = etree.parse(remote)
    records = tree.findall('.//' + OAI + 'record')
    return records

class Validator(object):
    """Validates OAI-OMH interfaces."""

    def __init__(self, base_url):
        super(Validator, self).__init__()
        if base_url.endswith('?'):
            self.base_url = base_url
        else:
            self.base_url = base_url + '?'

        try: 
            urllib2.urlopen(self.base_url)
            self.interface_reachable = True
            self.network_error = None
        except Exception, message:
            self.interface_reachable = False
            self.network_error = message
        
    def check_XML(self, verb, metadataPrefix='oai_dc'):
        """Check if XML response for OAI-PMH verb is well-formed."""
        if verb == 'Identify':
            try:
                remote = request_oai(self.base_url, verb)
                etree.parse(remote)
                return True
            except XMLSyntaxError, message:
                return message
        elif verb == 'ListRecords':
            try:
                remote = request_oai(self.base_url, verb, 
                                        metadataPrefix=metadataPrefix)
                etree.parse(remote)
                return True
            except XMLSyntaxError, message:
                return message


    def validate_XML(self, verb, metadataPrefix='oai_dc'):
        """Check if XML returned for OAI-PMH verb is valid."""
        if verb == 'Identify':
            try:
                remote = request_oai(self.base_url, verb)
                tree = etree.parse(remote)
            except XMLSyntaxError, message:
                return message
        elif verb == 'ListRecords':
            try:
                remote = request_oai(self.base_url, verb, 
                                        metadataPrefix=metadataPrefix)
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


    def reasonable_batch_size(self, verb, metadataPrefix='oai_dc', 
                            min_batch_size=100, max_batch_size=500):
        """
        Check if a reasonable number of data records is returned for a
        ListRecords/ListIdentifiers request. Return a tuple of
        (result, actual batch size). Result can be -1 (to small), 1 (too
        large) or 0 (reasonable size). Default values are set according
        to the DRIVER guidelines.
        """
        if verb == 'ListRecords':
            element = 'record'
        if verb == 'ListIdentifiers':
            element = 'header'
        records = get_records(self.base_url, metadataPrefix=metadataPrefix)
        batch_size = len(records)
        if batch_size < min_batch_size:
            return (-1, batch_size, min_batch_size)
        elif batch_size > max_batch_size:
            return (1, batch_size, max_batch_size)
        else:
            return (0, batch_size)


    def incremental_harvesting(self, verb, metadataPrefix='oai_dc'):
        """
        Check if server supports incremental harvesting by date (returns Boolean).
        """
        if verb == 'ListRecords':
            element = 'record'
        if verb == 'ListIdentifiers':
            element = 'header'
        
        remote = request_oai(self.base_url, verb, metadataPrefix=metadataPrefix)
        tree = etree.parse(remote)
        records = tree.findall('.//' + OAI + element)
        
        reference_record = random.sample(records, 1)[0]
        reference_datestamp = reference_record.find('.//' + OAI + 'datestamp').text
        reference_oai_id = reference_record.find('.//' + OAI + 'identifier').text
        
        remote = request_oai(self.base_url, verb, 
                            metadataPrefix=metadataPrefix, 
                            _from=reference_datestamp,
                            until=reference_datestamp)
        tree = etree.parse(remote)                    
        records = tree.findall('.//' + OAI + element)
        if len(records) > 1:
            return False
        test_record = records[0]
        test_oai_id = test_record.find('.//' + OAI + 'identifier').text
        if test_oai_id == reference_oai_id:
            return True
        else:
            return False
    
    def minimal_dc_elements(self):
        """
        Check for the minimal set of Dublin Core elements. Return True if OK
        or a dictionary of record IDs and missing elements if not.
        """
        err_dict = {}
        records = get_records(self.base_url)
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            dc_elements = record.findall('.//' + DC + '*')
            dc_tags = set([dc.tag[34:] for dc in dc_elements])
            if MINIMAL_DC_SET - dc_tags != set():
                err_dict[oai_id] = MINIMAL_DC_SET - dc_tags
        if err_dict == {}:
            return True 
        else:
            return err_dict
    
    
    def dc_date_ISO(self):
        """
        Check if dc:date conforms to ISO 8601 (matches YYYY-MM-DD).
        Return True if OK or a dictionary of record IDs and invalid dates if not.
        """
        err_dict = {}
        records = get_records(self.base_url)
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            dc_dates = record.findall('.//' + DC + 'date')
            for dc_date in dc_dates:
                if not re.match(DC_DATE_PATTERN, dc_date.text):
                    err_dict[oai_id] = dc_date.text
        if err_dict == {}:
            return True
        else:
            return err_dict
            
    def check_resumption_token(self, verb, metadataPrefix):
        """Make sure that the resumption token works."""
        pass
    