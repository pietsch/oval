# -*- coding: utf-8 -*-
#!/usr/bin/python
"""
    validator.py
    ~~~~~~~~~~~~

    The core module of oval.

    :copyright: Copyright 2011 Mathias Loesch.
"""

import os

import random
import urllib2
from urllib2 import URLError, HTTPError
import re
import argparse


from lxml import etree
from lxml.etree import XMLSyntaxError
from lxml.etree import DocumentInvalid

from oval.harvester import request_oai
from oval import DATA_PATH
from oval import ISO_639_3_CODES, ISO_639_2B_CODES
from oval import ISO_639_2T_CODES, ISO_639_1_CODES

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
                'creator'
])

# Date scheme according to ISO 8601
DC_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        
        
# Helper functions
def get_records(base_url, metadataPrefix='oai_dc'):
    """Shortcut for getting records in oai_dc from base_url. Returns a list of
    etree elements.
    """
    remote = request_oai(base_url, 'ListRecords', metadataPrefix=metadataPrefix)
    tree = etree.parse(remote)
    records = tree.findall('.//' + OAI + 'record')
    return records


class Validator(object):
    """Validates OAI-OMH interfaces."""

    def __init__(self, base_url):
        super(Validator, self).__init__()
        self.results = []
        if base_url.endswith('?'):
            self.base_url = base_url
        else:
            self.base_url = base_url + '?'
        try: 
            urllib2.urlopen(self.base_url)
        except Exception:
            raise
        
        try:
            remote = request_oai(self.base_url, 'Identify')
            tree = etree.parse(remote)
            self.repository_name = tree.find('.//' + OAI + 'repositoryName').text
            self.admin_email = tree.find('.//' + OAI + 'adminEmail').text
        except Exception:
            raise

    def check_XML(self, verb, metadataPrefix='oai_dc'):
        """Check if XML response for OAI-PMH verb is well-formed."""
        try:
            if verb == 'Identify':
                remote = request_oai(self.base_url, verb)
            elif verb == 'ListRecords':
                remote = request_oai(self.base_url, verb, 
                                    metadataPrefix=metadataPrefix)
        except Exception, exc:
            self.results.append(('%sWellFormed' % verb, 'unverified', exc.args[0]))
            return
        try:        
            etree.parse(remote)
            self.results.append(('%sWellFormed' % verb, 'ok', '%s response is well-formed' % verb))
        except XMLSyntaxError, exc:
            self.results.append(('%sWellFormed' % verb, 'error', exc.args[0]))


    def validate_XML(self, verb, metadataPrefix='oai_dc'):
        """Check if XML returned for OAI-PMH verb is valid."""
        try:
            if verb == 'Identify':
                remote = request_oai(self.base_url, verb)

            elif verb == 'ListRecords':
                remote = request_oai(self.base_url, verb, 
                                        metadataPrefix=metadataPrefix)
        except Exception, exc:
            self.results.append(('%sValid' % verb, 'unverified', exc.args[0]))
            return
        try:
            tree = etree.parse(remote)
        except XMLSyntaxError:
            self.results.append(('%sValid' % verb, 'error', exc.args[0]))
            return
        schema_file = os.path.join(DATA_PATH, 'combined.xsd')
        schema_tree = etree.parse(schema_file)
        schema = etree.XMLSchema(schema_tree)
        try:
            schema.assertValid(tree)
            self.results.append(('%sValid' % verb, 'ok', '%s response is valid.' % verb))
        except DocumentInvalid, exc:
            self.results.append(('%sValid' % verb, 'error', exc.args[0]))

    def reasonable_batch_size(self, verb, metadataPrefix='oai_dc', 
                            min_batch_size=100, max_batch_size=500):
        """Check if a reasonable number of data records is returned for a
        ListRecords/ListIdentifiers request. Default values are set according
        to the DRIVER guidelines.
        """
        if verb == 'ListRecords':
            element = 'record'
        if verb == 'ListIdentifiers':
            element = 'header'
        
        try:
            remote = request_oai(self.base_url, verb, 
                                metadataPrefix=metadataPrefix)
            tree = etree.parse(remote)
        except Exception, exc:
            self.results.append(('%sBatch' % verb, 'unverified', exc.args[0]))
            return
        
        records = tree.findall('.//' + OAI + element)        
        batch_size = len(records)
        if batch_size < min_batch_size:
            message = '%s batch too small (%d), should be at least %d.' % \
                       (verb, batch_size, min_batch_size)
            self.results.append(('%sBatch' % verb, 'recommendation', message))
        elif batch_size > max_batch_size:
            message = '%s batch too large (%d), should be at most %d.' % \
                       (verb, batch_size, min_batch_size)
            self.results.append(('%sBatch' % verb, 'recommendation', message))
        else:
            message = '%s batch size is OK (%d).' % (verb, batch_size)
            self.results.append(('%sBatch' % verb, 'ok', message))

    def incremental_harvesting(self, verb, metadataPrefix='oai_dc'):
        """Check if server supports incremental harvesting by date (returns
        Boolean).
        """
        if verb == 'ListRecords':
            element = 'record'
        if verb == 'ListIdentifiers':
            element = 'header'
        try:
            remote = request_oai(self.base_url, verb, metadataPrefix=metadataPrefix)
            tree = etree.parse(remote)
        except Exception, exc:
            self.results.append(('Incremental%s' % verb, 'unverified', exc.args[0]))
            return
        records = tree.findall('.//' + OAI + element)
        
        # Draw a reference record
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
            self.results.append(('Incremental%s' % verb, 'error', 'No incremental harvesting.'))
        test_record = records[0]
        test_oai_id = test_record.find('.//' + OAI + 'identifier').text
        if test_oai_id == reference_oai_id:
            self.results.append(('Incremental%s' % verb, 'ok', 'Incremental harvesting works.'))
        else:
            self.results.append(('Incremental%s' % verb, 'error', 'No incremental harvesting.'))

    def minimal_dc_elements(self, minimal_set=MINIMAL_DC_SET):
        """Check for the minimal set of Dublin Core elements. Return True if OK.
        Raise MinimalDCError otherwise.
        """
        try:
            records = get_records(self.base_url)
        except Exception, exc:
            self.results.append(('MinimalDC', 'unverified', exc.args[0]))
            return
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            dc_elements = record.findall('.//' + DC + '*')
            dc_tags = set([dc.tag[34:] for dc in dc_elements])
            intersect = minimal_set - dc_tags
            if intersect != set():
                message = '''Every record should at least contain the following DC elements: %s
Found a record (%s) missing the following DC element(s): %s'''
                self.results.append(
                                     (
                                     'MinimalDC', 
                                     'warning', message \
                                                % (", ".join(minimal_set), 
                                                    oai_id, 
                                                    ", ".join(intersect)
                                                  )
                                      )
                )
                return
        self.results.append(('MinimalDC', 'ok', 'Minimal DC elments are present.'))

    def dc_date_ISO(self):
        """Check if dc:date conforms to ISO 8601 (matches YYYY-MM-DD). Return
        True if OK or a dictionary of record IDs and invalid dates if not.
        """
        err_dict = {}
        records = get_records(self.base_url)
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            dc_dates = record.findall('.//' + DC + 'date')
            for dc_date in dc_dates:
                if not re.match(DC_DATE_PATTERN, dc_date.text):
                    message = '''Found a record (%s) whose dc:date is not
conforming to ISO 8601''' % oai_id
                    self.results.append(('ISO8601', 'error', message))
                    return
        self.results.append(('ISO8601', 'ok', 'dc:dates conform to ISO 8601.'))

    def dc_language_ISO(self):
        """Check if dc:language conforms to ISO 639-3/-2B/-2T/-1."""
        records = get_records(self.base_url)
        test_record = random.sample(records, 1)[0]
        oai_id = test_record.find('.//' + OAI + 'identifier').text
        language_elements = test_record.findall('.//' + DC + 'language')
        
        for language_element in language_elements:
            language = language_element.text
            if language in ISO_639_3_CODES:
                iso = '639-3'
            elif language in ISO_639_2B_CODES:
                iso = '639-2B'
            elif language in ISO_639_2T_CODES:
                iso = '639-2T'
            elif language in ISO_639_1_CODES:
                iso = '639-1'
            else:
                iso = None
        if iso is None:
            message = 'dc:language should conform to ISO 639, found %s.' % language
            self.results.append(('ISO639', 'recommendation', message))
        else:
            message = 'dc:language conforms to ISO %s.' % iso
            self.results.append(('ISO639', 'ok', message))

    def check_resumption_token(self, verb, metadataPrefix, batches=1):
        """Make sure that the resumption token works. Check as many batches
        as specified (default: 1).
        """
        pass

    def check_driver_conformity(self):
        """Run checks required for conformance to DRIVER guidelines"""
        self.check_XML('Identify')
        self.check_XML('ListRecords')
        self.validate_XML('Identify')
        self.validate_XML('ListRecords')
        self.reasonable_batch_size('ListRecords')
        self.reasonable_batch_size('ListIdentifiers')
        self.dc_date_ISO()
        self.minimal_dc_elements()


def main():
    """Command line interface."""
    from pprint import pprint
    parser = argparse.ArgumentParser(description='OVAL -- OAI-PHM Validator')
    parser.add_argument('base_url', type=str, help='the basic URL of the OAI-PMH interface')
    parser.add_argument('--driver', dest='driver', action='store_true', 
                        default=False, help='check conformance to DRIVER guidelines')
                        
    args = parser.parse_args()
    
    base_url = args.base_url
    driver = args.driver
    
    val = Validator(base_url)
    
    print "Repository: %s" % val.repository_name
    
    if driver:
        val.check_driver_conformity()
        pprint(val.results)
        
if __name__ == '__main__':
    main()