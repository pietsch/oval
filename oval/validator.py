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
import re
import argparse
import pickle
from urlparse import urlparse
from dateutil import parser as dateparser


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

# Date schemes according to ISO 8601 (increasing granularity)
DC_DATE_YEAR = re.compile(r'^\d{4}$')
DC_DATE_MONTH = re.compile(r'^\d{4}-\d{2}$')
DC_DATE_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DC_DATE_FULL = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$')

# URLs of Repositories indexed in BASE 
BASE_URLS = pickle.load(open(os.path.join(DATA_PATH, 'BASE_URLS.pickle')))

        
# Helper functions
def get_records(base_url, metadataPrefix='oai_dc'):
    """Shortcut for getting records in oai_dc from base_url. Returns a list of
    etree elements.
    """
    remote = request_oai(base_url, 'ListRecords', metadataPrefix=metadataPrefix)
    tree = etree.parse(remote)
    records = tree.findall('.//' + OAI + 'record')
    return records

def get_random_record(base_url, metadataPrefix='oai_dc'):
    """Shortcut for getting a random record in oai_dc."""
    remote = request_oai(base_url, 'ListRecords', metadataPrefix=metadataPrefix)
    tree = etree.parse(remote)
    records = tree.findall('.//' + OAI + 'record')
    random_record = random.sample(records, 1)[0]
    return random_record


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
        
        methods = ['POST', 'GET']
        #HTTP-Method
        supported_methods = self.check_HTTP_methods(methods)
        if len(supported_methods) == 2:
            message = 'Server supports both GET and POST method.'
            self.results.append(('HTTPMethod', 'ok', message))
            self.method = 'POST'
        elif len(supported_methods) == 1:
            supported_method = supported_methods[0]
            message = 'Server accepts only %s requests.' % supported_method
            self.results.append(('HTTPMethod', 'error', message))
            self.method = supported_method
        
        remote = request_oai(self.base_url, 'Identify', method=self.method)
        tree = etree.parse(remote)
        self.repository_name = tree.find('.//' + OAI + 'repositoryName').text
        self.admin_email = tree.find('.//' + OAI + 'adminEmail').text
        
    
    def check_HTTP_methods(self, methods):
        """Make sure server supports GET and POST as required. Return supported
        method(s).
        """
        methods = methods
        for method in methods:
            remote = request_oai(self.base_url, 'Identify', method=method)
            tree = etree.parse(remote)
            error = tree.find('.//' + OAI + 'error')
            if error is not None:
                methods.remove(method)
        return methods
    
    def indexed_in_BASE(self):
        """Check if the repository is indexed in BASE."""
        netloc = urlparse(self.base_url).netloc
        if netloc in BASE_URLS:
            message = "Repository content is indexed by BASE."
        else:
            message = "Repository content is indexed by BASE."
        self.results.append(('BASEIndex', 'info', message))
    
    def check_identify_base_url(self):
        """Compare field baseURL in Identify response with self.base_url."""
        try:
            remote = request_oai(self.base_url, 'Identify', method=self.method)
            tree = etree.parse(remote)
            request_field = tree.find('.//' + OAI + 'request')
        except Exception, exc:
            message = "Could not compare basic URLs: %s" % exc.args[0]
            self.results.append(('BaseURLMatch', 'unverified', message))
            return
        if request_field is None:
            message = "Could not compare basic URLs: field request not found."
            self.results.append(('BaseURLMatch', 'unverified', message))
            return
        request_url = request_field.text
        if self.base_url[:-1] == request_url:
            message = 'URL in "request" (Identify) matches provided basic URL.'
            self.results.append(('BaseURLMatch', 'ok', message))
        else:
            message = 'Requests seem to be redirected to: "%s"' % request_url
            self.results.append(('BaseURLMatch', 'warning', message))
            
    def check_XML(self, verb, metadataPrefix='oai_dc', identifier=None):
        """Check if XML response for OAI-PMH verb is well-formed."""
        try:
            if verb in ('Identify', 'ListSets', 'ListMetadataFormats'):
                remote = request_oai(self.base_url, verb, method=self.method)
            elif verb in ('ListRecords', 'ListIdentifiers'):
                remote = request_oai(self.base_url, verb, method=self.method,
                                    metadataPrefix=metadataPrefix, 
                                    identifier=identifier)                
        except Exception, exc:
            message = "Well-formedness of %s could not be checked: %s" % (verb,
                                                                        exc.args[0])
            self.results.append(('%sWellFormed' % verb, 'unverified', message))
            return
        try:        
            etree.parse(remote)
            self.results.append(('%sWellFormed' % verb, 'ok', '%s response is '
                                'well-formed.' % verb))
        except XMLSyntaxError, exc:
            message = '%s response is not well-formed: %s' % (verb, exc.args[0])
            self.results.append(('%sWellFormed' % verb, 'error', message))


    def validate_XML(self, verb, metadataPrefix='oai_dc', identifier=None):
        """Check if XML returned for OAI-PMH verb is valid."""
        try:
            if verb in ('Identify', 'ListSets', 'ListMetadataFormats'):
                remote = request_oai(self.base_url, verb, method=self.method)

            elif verb in ('ListRecords', 'ListIdentifiers', 'GetRecord'):
                remote = request_oai(self.base_url, verb, method=self.method,
                                        metadataPrefix=metadataPrefix, 
                                        identifier=identifier)
            tree = etree.parse(remote)
        except Exception, exc:
            message = 'Validity of %s could not be checked: %s' % (verb,
                                                                    exc.args[0])
            self.results.append(('%sValid' % verb, 'unverified', message))
            return
        schema_file = os.path.join(DATA_PATH, 'combined.xsd')
        schema_tree = etree.parse(schema_file)
        schema = etree.XMLSchema(schema_tree)
        try:
            schema.assertValid(tree)
            self.results.append(('%sValid' % verb, 'ok', '%s response is valid.' % verb))
        except DocumentInvalid, exc:
            message = "%s response is invalid. %s" % (verb, exc.args[0])
            self.results.append(('%sValid' % verb, 'error', message))

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
            remote = request_oai(self.base_url, verb, method=self.method,
                                metadataPrefix=metadataPrefix)
            tree = etree.parse(remote)
        except Exception, exc:
            message = "%s batch size could not be checked: %s" % (verb, exc.args[0])
            self.results.append(('%sBatch' % verb, 'unverified', message))
            return
        
        records = tree.findall('.//' + OAI + element)
        batch_size = len(records)
        
        if batch_size == 0:
            message = ('%s batch size could not be checked: No records.' % verb)
            self.results.append(('%sBatch' % verb, 'unverified', message))
            return
        if batch_size < min_batch_size:
            message = ('%s batch size too small (%d), should be at least %d.' %
                       (verb, batch_size, min_batch_size))
            self.results.append(('%sBatch' % verb, 'recommendation', message))
        elif batch_size > max_batch_size:
            message = ('%s batch size is too large (%d), should be at most %d.' %
                       (verb, batch_size, max_batch_size))
            self.results.append(('%sBatch' % verb, 'recommendation', message))
        else:
            message = '%s batch size is %d.' % (verb, batch_size)
            self.results.append(('%sBatch' % verb, 'ok', message))

    def incremental_harvesting(self, verb, metadataPrefix='oai_dc'):
        """Check if server supports incremental harvesting by date.
        """
        if verb == 'ListRecords':
            element = 'record'
        if verb == 'ListIdentifiers':
            element = 'header'
        try:
            remote = request_oai(self.base_url, verb, method=self.method,
                                metadataPrefix=metadataPrefix)
            tree = etree.parse(remote)
            records = tree.findall('.//' + OAI + element)
        except Exception, exc:
            message = "Incremental harvesting could not be checked: %s" % exc.args[0]
            self.results.append(('Incremental%s' % verb, 'unverified', 
                                message))
            return
        if len(records) == 0:
            message = "Incremental harvesting could not be checked: No records."
            self.results.append(('Incremental%s' % verb, 'unverified', 
                                message))
            return
        reference_record = random.sample(records, 1)[0]
        reference_datestamp_elem = reference_record.find('.//' + OAI + 'datestamp')
        if reference_datestamp_elem is None:
            message = "Incremental harvesting could not be checked: No no datestamp."
            self.results.append(('Incremental%s' % verb, 'unverified', 
                                message))
            return
        reference_datestamp = reference_datestamp_elem.text[:10]
        try:
            remote = request_oai(self.base_url, verb, method=self.method,
                                metadataPrefix=metadataPrefix, 
                                _from=reference_datestamp,
                                until=reference_datestamp)
            tree = etree.parse(remote)
        except Exception, exc:
            message = "Incremental harvesting could not be checked: %s" % exc.args[0]
            self.results.append(('Incremental%s' % verb, 'unverified', 
                                message))
            return
        records = tree.findall('.//' + OAI + element)
        if len(records) == 0:
            self.results.append(('Incremental%s' % verb, 'error', 
                                'No incremental harvesting of %s.' % verb))
            return
        test_record = random.sample(records, 1)[0]
        test_datestamp = test_record.find('.//' + OAI + 'datestamp').text[:10]
        if test_datestamp == reference_datestamp:
            self.results.append(('Incremental%s' % verb, 'ok', 
                                'Incremental harvesting of %s works.' % verb))
        else:
            self.results.append(('Incremental%s' % verb, 'error', 
                                'No incremental harvesting of %s.' % verb))

    def minimal_dc_elements(self, minimal_set=MINIMAL_DC_SET):
        """Check for the minimal set of Dublin Core elements."""
        try:
            records = get_records(self.base_url)
        except Exception, exc:
            message = 'Minimal DC elements could not be checked: %s' % exc.args[0]
            self.results.append(('MinimalDC', 'unverified', message))
            return
        if len(records) == 0:
            message = "Minimal DC elements could not be checked: No records."
            self.results.append(('MinimalDC', 'unverified', 
                                message))
            return
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            dc_elements = record.findall('.//' + DC + '*')
            # Remove the namespace from dc:tags
            dc_tags = set([dc.tag.replace(DC, '') for dc in dc_elements])
            intersect = minimal_set - dc_tags
            if intersect != set():
                message = ("Every record should at least contain the DC "
                          "elements: %s. Found a record (%s) missing the "
                          "following DC element(s): %s.")
                self.results.append(('MinimalDC', 'warning', message % (
                                                         ", ".join(minimal_set),
                                                          oai_id, 
                                                        ", ".join(intersect))))
                return
        self.results.append(('MinimalDC', 'ok', 'Minimal DC elements (%s) are '
                            'present.' % ', '.join(minimal_set)))

    def dc_date_ISO(self):
        """Check if dc:date conforms to ISO 8601 (matches YYYY-MM-DD). Return
        True if OK or a dictionary of record IDs and invalid dates if not.
        """
        err_dict = {}
        try:
            records = get_records(self.base_url)
        except Exception, exc:
            message = 'dc:date ISO 8601 conformance could not be checked: %s' % exc.args[0]
            self.results.append(('ISO8601', 'unverified', message))
            return
        if len(records) == 0:
            message = "dc:date ISO 8601 conformance could not be checked: No records."
            self.results.append(('ISO8601', 'unverified', 
                                message))
            return
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            dc_dates = record.findall('.//' + DC + 'date')
            for dc_date in dc_dates:
                date = dc_date.text
                if not (DC_DATE_YEAR.match(date) or
                        DC_DATE_MONTH.match(date) or
                        DC_DATE_DAY.match(date) or 
                        DC_DATE_FULL.match(date)):
                    message = ('Found a record (%s) where the content of dc:date '
                        'is not conforming to ISO 8601: "%s"' % (oai_id, date))
                    self.results.append(('ISO8601', 'warning', message))
                    return
        self.results.append(('ISO8601', 'ok', 'dc:dates conform to ISO 8601.'))

    def dc_language_ISO(self):
        """Check if dc:language conforms to ISO 639-3/-2B/-2T/-1."""
        try:
            remote = request_oai(self.base_url, 'ListRecords', method=self.method,
                                metadataPrefix='oai_dc')
            tree = etree.parse(remote)
        except Exception, exc:
            message = 'dc:language conformance to ISO 639 could not be checked: %s' % exc.args[0]
            self.results.append(('ISO639', 'unverified', message))
            return
        language_elements = tree.findall('.//' + DC + 'language')
        if language_elements == []:
            message = ('dc:language conformance to ISO 639 could not be checked: '
                      'No dc:language element found.')
            self.results.append(('ISO639', 'unverified', message))
            return
        records = tree.findall('.//' + OAI + 'record')
        for record in records:
            oai_id = record.find('.//' + OAI + 'identifier').text
            language_elements = record.findall('.//' + DC + 'language')
            if language_elements == []:
                continue
            for language_element in language_elements:
                try:
                    language = language_element.text
                except AttributeError:
                    continue
                if language in ISO_639_3_CODES:
                    iso = '639-3'
                elif language in ISO_639_2B_CODES:
                    iso = '639-2B'
                elif language in ISO_639_2T_CODES:
                    iso = '639-2T'
                elif language in ISO_639_1_CODES:
                    iso = '639-1'
                else:
                    message = ('dc:language should conform to ISO 639, '
                            'found "%s" (%s).' % (language, oai_id))
                    self.results.append(('ISO639', 'recommendation', message))
                    return  
        message = 'dc:language conforms to ISO %s.' % iso
        self.results.append(('ISO639', 'ok', message))

    def check_resumption_token(self, verb, metadataPrefix, batches=1):
        """Make sure that the resumption token works. Check as many batches
        as specified (default: 1).
        """
        pass

    def check_deleting_strategy(self):
        """Report the deleting strategy; recommend persistent or transient"""
        try:
            remote = request_oai(self.base_url, 'Identify', method=self.method)
            tree = etree.parse(remote)
            deleting_strategy = tree.find('.//' + OAI + 'deletedRecord').text
        except AttributeError:
            message = "Deleting strategy could not be checked: deletedRecord element not found."
            self.results.append(('DeletingStrategy', 'unverified', message))
            return
        except Exception, exc:
            message = "Deleting strategy could not be checked: %s" % exc.args[0]
            self.results.append(('DeletingStrategy', 'unverified', message))
            return
        if deleting_strategy == 'no':
            message = (u"No deleting strategy – recommended is persistent or "
                      "transient.")
            report = 'recommendation'    
        elif deleting_strategy in ('transient', 'persistent'):
            message = 'Deleting strategy is "%s"' % deleting_strategy
            report = 'ok'
        else:
            message = 'Undefined deleting strategy: "%s"' % deleting_strategy
            report = 'error'
        self.results.append(('DeletingStrategy', report, message))

    def dc_identifier_abs(self):
        """Check if dc:identifier contains an absolute URL."""
        try:
            records = get_records(self.base_url)
        except Exception, exc:
            message = "Could not check URL in dc:identifier: %s" % exc.args[0]
            self.results.append('DCIdentifierURL', 'error', message)
            return
        if len(records) == 0:
            message = "Could not check URL in dc:identifier: No records."
            self.results.append(('DCIdentifierURL', 'unverified', message))
            return
        found_abs_urls = set()
        for record in records:
            abs_url = False
            oai_id = record.find('.//' + OAI + 'identifier').text
            identifiers = record.findall('.//' + DC + 'identifier')
            if identifiers == []:
                message = ("Found at least one record missing dc:identifier: %s"
                            % oai_id)
                self.results.append(('DCIdentifierURL', 'warning', message))
                return
            for identifier_element in identifiers:
                identifier = identifier_element.text
                if urlparse(identifier).scheme == 'http':
                    abs_url = True
                    found_abs_urls.add(identifier)
            if abs_url == False:
                message = ("Found at least one record missing an absolute URL "
                           "in dc:identifier: %s" % oai_id)
                self.results.append(('DCIdentifierURL', 'warning', message))
                return
        if len(records) > 1 and len(found_abs_urls) == 1:
            message = ("All records have the same URL in dc:identifier: %s"
                        % list(found_abs_urls)[0])
            self.results.append(('DCIdentifierURL', 'warning', message))
            return
        message = "Every record contains an absolute URL in dc:identifier."
        self.results.append(('DCIdentifierURL', 'ok', message))
                
    def check_driver_conformity(self):
        """Run checks required for conformance to DRIVER guidelines"""
        self.check_identify_base_url()
        self.check_XML('Identify')
        self.check_XML('ListRecords')
        self.check_XML('ListIdentifiers')
        self.check_XML('ListSets')
        self.validate_XML('Identify')
        self.validate_XML('ListRecords')
        self.validate_XML('ListIdentifiers')
        self.validate_XML('ListSets')
        self.reasonable_batch_size('ListRecords')
        self.reasonable_batch_size('ListIdentifiers')
        self.dc_language_ISO()
        self.dc_date_ISO()
        self.minimal_dc_elements()
        self.incremental_harvesting('ListRecords')
        self.dc_identifier_abs()
        self.check_deleting_strategy()
        self.indexed_in_BASE()

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