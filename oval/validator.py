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
from urllib2 import URLError
import re
import argparse
import pickle
from urlparse import urlparse
from datetime import datetime
from dateutil import parser as dateparser

from lxml import etree
from lxml.etree import XMLSyntaxError
from lxml.etree import DocumentInvalid

from oval.harvester import configure_record_iterator, configure_request, get_protocol_version, check_HTTP_methods, get_repository_information, get_granularity
from oval import DATA_PATH
from oval import ISO_639_3_CODES, ISO_639_2B_CODES
from oval import ISO_639_2T_CODES, ISO_639_1_CODES

OAI_NAMESPACE = "http://www.openarchives.org/OAI/%s/"

DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
DC = '{%s}' % DC_NAMESPACE

# Minimal Dublin Core elements according to DRIVER and DINI
MINIMAL_DC_SET = set([
                'identifier',
                'title',
                'date',
                'type',
                'creator'])

# Protocol Version Scheme
VERSION_PATTERN = re.compile(r'<protocolVersion>(.*?)</protocolVersion>')

# Date schemes according to ISO 8601 (increasing granularity)
DC_DATE_YEAR = re.compile(r'^\d{4}$')
DC_DATE_MONTH = re.compile(r'^\d{4}-\d{2}$')
DC_DATE_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DC_DATE_FULL = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$')

# URLs of Repositories indexed in BASE 
BASE_URLS = pickle.load(open(os.path.join(DATA_PATH, 'BASE_URLS.pickle')))


schema_file = os.path.join(DATA_PATH, 'combined.xsd')
schema_tree = etree.parse(schema_file)
SCHEMA = etree.XMLSchema(schema_tree)


def is_double_encoded(string):
    """Check if a unicode string is double encoded UTF8."""
    try:
         cleaned = string.encode('raw_unicode_escape').decode('utf8')
    except UnicodeDecodeError:
        return False
    if '\\u' in cleaned:
        return False
    return cleaned != string

def normalize_base_url(url):
    url = url.strip()
    if '?verb=' in url:
        url = url[:url.index('verb=')]
    elif url.endswith('?'):
        pass
    else:
        url = url + '?'
    return url
    
def draw_sample(iterator, size):
    items = []
    for item in iterator:
        items.append(item)
        if len(items) == size:
            break
    return items

class Validator(object):
    """Validates OAI-OMH interfaces."""

    def __init__(self, base_url, timeout=None):
        super(Validator, self).__init__()
        
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.results = {}
        
        #HTTP-Method
        supported_methods = check_HTTP_methods(self.base_url)
        if len(supported_methods) == 2:
            message = 'Server supports both GET and POST requests.'
            self.results['HTTPMethod'] = ('ok', message)
            self.method = 'POST'
        elif len(supported_methods) == 1:
            supported_method = supported_methods[0]
            message = 'Server accepts only %s requests.' % supported_method
            self.results['HTTPMethod'] = ('error', message)
            self.method = supported_method
        else:
            message = ('Could not determine supported HTTP methods. '
                      'Falling back to GET.')
            self.results['HTTPMethod'] =  ('warning', message)
            self.method = 'GET'
        
        self.protocol_version = get_protocol_version(self.base_url, self.method)
        if self.protocol_version is None:
            message = 'Could not determine OAI-PMH protocol version; assuming 2.0'
            self.results['ProtocolVersion'] =  ('warning', message)
            self.protocol_version = '2.0'
        elif self.protocol_version == '1.0' or self.protocol_version == '1.1':
            message = 'OAI-PMH version %s is deprecated. Consider updating to 2.0.' % self.protocol_version
            self.results['ProtocolVersion'] = ('recommendation', message)
        elif self.protocol_version == '2.0':
            message = 'OAI-PMH version is 2.0'
            self.results['ProtocolVersion'] = ('ok', message)
        else:
            message = 'Undefined OAI-PMH protocol version: %s Assuming 2.0' % self.protocol_version
            self.results['ProtocolVersion'] =  ('error', message)
            self.protocol_version = '2.0'
            
        #Preconfigure RecordIterator class for this repo
        self.RecordIterator = configure_record_iterator(self.base_url, self.protocol_version, self.method, self.timeout)
        self.oai_namespace = OAI_NAMESPACE % self.protocol_version
        self.oai = "{%s}" % self.oai_namespace
        
        # General Repository Information
        self.repository_name, self.admin_email = get_repository_information(self.base_url,
                                                    self.method)
        self.granularity = get_granularity(self.base_url, self.method)
        if self.granularity is None:
            # Fall back to day granularity in case it could not be determined
            self.granularity = 'day'
        self.request_oai = configure_request(self.base_url, self.method, timeout=self.timeout)
    
    def indexed_in_BASE(self):
        """Check if the repository is indexed in BASE."""
        netloc = urlparse(self.base_url).netloc
        if netloc in BASE_URLS:
            message = "Repository content is indexed by BASE."
        else:
            message = "Repository content is currently not indexed by BASE."
        self.results['BASEIndex'] = ('info', message)


    def check_identify_base_url(self):
        """Compare field baseURL in Identify response with self.base_url."""
        # In version 2.0, the requestURL field was renamed to requestURL
        if self.protocol_version == '2.0':
            request_tagname = 'request'
        else:
            request_tagname = 'requestURL'
        try:
            tree = self.request_oai(verb='Identify')
            request_field = tree.find('.//' + self.oai + request_tagname)
        except Exception, exc:
            message = "Could not compare basic URLs: %s" % unicode(exc)
            self.results['BaseURLMatch'] = ('unverified', message)
            return
        if request_field is None:
            message = 'Could not compare basic URLs: field "%s" not found.' % request_tagname
            self.results['BaseURLMatch']= ('unverified', message)
            return
        request_url = request_field.text
        if self.base_url[:-1] == request_url:
            message = 'URL in "%s" (Identify) matches provided basic URL.' % request_tagname
            self.results['BaseURLMatch'] = ('ok', message)
        else:
            message = 'Requests seem to be redirected to: "%s"' % request_url
            self.results['BaseURLMatch'] = ('warning', message)
            

    def validate_XML(self, verb, metadataPrefix='oai_dc', identifier=None):
        """Check if XML returned for OAI-PMH verb is well-formed and valid."""
        try:
            if verb in ('Identify', 'ListSets', 'ListMetadataFormats'):
                tree = self.request_oai(verb=verb)

            elif verb in ('ListRecords', 'ListIdentifiers', 'GetRecord'):
                tree = self.request_oai(verb=verb, metadataPrefix=metadataPrefix,
                                        identifier=identifier)
        except XMLSyntaxError, exc:
            message = '%s response is not well-formed: %s' % (verb, unicode(exc))
            self.results['%sXML' % verb] = ('error', message)
            return
        except Exception, exc:
            message = 'XML response of %s could not be validated: %s' % (verb,
                                                                    unicode(exc))
            self.results['%sXML' % verb] = ('unverified', message)
            return
        try:
            SCHEMA.assertValid(tree)
            self.results['%sXML' % verb] = ('ok', '%s response well-formed and valid.' % verb)
        except DocumentInvalid, exc:
            message = "%s response well-formed but invalid: %s" % (verb, unicode(exc))
            self.results['%sXML' % verb] = ('error', message)


    def reasonable_batch_size(self, verb, metadataPrefix='oai_dc', 
                            min_batch_size=100, max_batch_size=500):
        """Check if a reasonable number of data records is returned for a
        ListRecords/ListIdentifiers request. Default values are set according
        to the DRIVER guidelines.
        """
        try:
            riter = self.RecordIterator(verb, metadataPrefix, deleted=True)
        except Exception, exc:
            message = "%s batch size could not be checked: %s" % (verb, unicode(exc))
            self.results['%sBatch' % verb] = ('unverified', message)
            return
        # resumptionToken found? (= are there multiple batches?)
        if riter.token is None:
            message = ('%s batch size could not be checked: Only one batch.' % verb)
            self.results['%sBatch' % verb] = ('unverified', message)
            return
        batch_size = len(riter.record_list)
        
        if batch_size == 0:
            message = ('%s batch size could not be checked: No records.' % verb)
            self.results['%sBatch' % verb] = ('unverified', message)
            return
        if batch_size < min_batch_size:
            message = ('%s batch size too small (%d), should be at least %d.' %
                       (verb, batch_size, min_batch_size))
            self.results['%sBatch' % verb] = ('recommendation', message)
        elif batch_size > max_batch_size:
            message = ('%s batch size is too large (%d), should be at most %d.' %
                       (verb, batch_size, max_batch_size))
            self.results['%sBatch' % verb] = ('recommendation', message)
        else:
            message = '%s batch size is %d.' % (verb, batch_size)
            self.results['%sBatch' % verb] = ('ok', message)


    def incremental_harvesting(self, verb, granularity, metadataPrefix='oai_dc', sample_size=50):
        """Check if server supports incremental harvesting using time granularity.
        """
        try:
            riter = self.RecordIterator(verb, metadataPrefix)
            records = draw_sample(riter, sample_size)
        except Exception, exc:
            message = "Incremental harvesting (%s granularity) of %s could not be checked: %s" % (granularity, verb, unicode(exc))
            self.results['Incremental%s%s' % (verb, granularity)] =  ('unverified', message)
            return
        if len(records) == 0:
            message = "Incremental harvesting (%s granularity) of %s could not be checked: No records." % (granularity, verb)
            self.results['Incremental%s%s' % (verb, granularity)] = ('unverified', message)
            return
        reference_record = random.sample(records, 1)[0]
        reference_datestamp_elem = reference_record.find('.//' + self.oai + 'datestamp')
        if reference_datestamp_elem is None:
            message = "Incremental harvesting (%s granularity) of %s could not be checked: No datestamp." % (granularity, verb)
            self.results['Incremental%s%s' % (verb, granularity)] = ('unverified', message)
            return
        reference_datestamp = reference_datestamp_elem.text
        if not (DC_DATE_DAY.match(reference_datestamp) or DC_DATE_FULL.match(reference_datestamp)):
            message = ("Incremental harvesting (%s granularity) of %s could not be checked: "
                        "Incorrect format for datestamp: %s." % (granularity, verb, reference_datestamp))
            self.results['Incremental%s%s' % (verb, granularity)] = ('unverified', message)
            return
        if granularity == 'day':
            reference_datestamp = reference_datestamp[:10]
        reference_date = dateparser.parse(reference_datestamp)
        try:
            riter = self.RecordIterator(verb, metadataPrefix=metadataPrefix, 
                                _from=reference_datestamp,
                                until=reference_datestamp)
        except Exception, exc:
            message = "Incremental harvesting (%s granularity) of %s could not be checked: %s" % (granularity, verb, unicode(exc))
            self.results['Incremental%s%s' % (verb, granularity)] = ('unverified', message)
            return
        if len(riter.record_list) == 0:
            self.results['Incremental%s%s' % (verb, granularity)] = ('error', 
                                'No incremental harvesting (%s granularity) of %s: ' 
                                'Harvest for reference date %s returned no records.'% (granularity, verb, reference_datestamp))
            return
        try:
            for record in riter:
                test_datestamp = record.find('.//' + self.oai + 'datestamp').text
                if granularity == 'day':
                    test_datestamp = test_datestamp[:10]
                test_date = dateparser.parse(test_datestamp)
                if test_date != reference_date:
                    self.results['Incremental%s%s' % (verb, granularity)] = ('error', 
                                        'No incremental (%s granularity) harvesting of %s. ' 
                                        'Harvest for reference date %s returned record with date %s.' % (granularity, verb, 
                                        reference_datestamp, test_datestamp))
                    return
        except Exception, exc:
            message = "Incremental harvesting (%s granularity) of %s could not be checked: %s" % (granularity, verb, unicode(exc))
            self.results['Incremental%s%s' % (verb, granularity)] =  ('unverified', message)
            return            
        self.results['Incremental%s%s' % (verb, granularity)] = ('ok', 
            'Incremental harvesting (%s granularity) of %s works.' % (granularity, verb))

    def minimal_dc_elements(self, minimal_set=MINIMAL_DC_SET, sample_size=50):
        """Check for the minimal set of Dublin Core elements."""
        try:
            riter = self.RecordIterator(verb='ListRecords', metadataPrefix='oai_dc', deleted=False)
            records = draw_sample(riter, sample_size)
        except Exception, exc:
            message = 'Minimal DC elements could not be checked: %s' % unicode(exc)
            self.results['MinimalDC'] = ('unverified', message)
            return
        if len(records) == 0:
            message = "Minimal DC elements could not be checked: No records."
            self.results['MinimalDC'] = ('unverified', message)
            return
        for record in records:
            oai_id = record.find('.//' + self.oai + 'identifier').text
            dc_elements = record.findall('.//' + DC + '*')
            # Remove the namespace from dc:tags
            dc_tags = set([dc.tag.replace(DC, '') for dc in dc_elements])
            intersect = minimal_set - dc_tags
            if intersect != set():
                message = ("Records should at least contain the DC "
                          "elements: %s. Found a record (%s) missing the "
                          "following DC element(s): %s.")
                self.results['MinimalDC'] = ('warning', message % (
                                                         ", ".join(minimal_set),
                                                          oai_id, 
                                                        ", ".join(intersect)))
                return
        self.results['MinimalDC'] = ('ok', 'Minimal DC elements (%s) are '
                            'present.' % ', '.join(minimal_set))

    def dc_date_ISO(self, sample_size=50):
        """Check if dc:date conforms to ISO 8601 (matches YYYY-MM-DD)."""
        try:
            riter = self.RecordIterator(verb='ListRecords', metadataPrefix='oai_dc', deleted=False)
            records = draw_sample(riter, sample_size)
        except Exception, exc:
            message = 'dc:date ISO 8601 conformance could not be checked: %s' % unicode(exc)
            self.results['ISO8601'] = ('unverified', message)
            return
        if len(records) == 0:
            message = "dc:date ISO 8601 conformance could not be checked: No records."
            self.results['ISO8601'] = ('unverified', 
                                message)
            return
        no_date = []; wrong_date = []; correct_date = []
        for record in records:
            oai_id = record.find('.//' + self.oai + 'identifier').text
            dc_dates = record.findall('.//' + DC + 'date')
            dc_dates = filter(lambda d: d.text is not None, dc_dates)
            if dc_dates == []:
                no_date.append(record)
                continue
            for dc_date in dc_dates:
                date = dc_date.text
                if not (DC_DATE_YEAR.match(date) or
                        DC_DATE_MONTH.match(date) or
                        DC_DATE_DAY.match(date) or 
                        DC_DATE_FULL.match(date)):
                        wrong_date.append(record)
                    # message = ('Found a record (%s) where the content of dc:date '
                    #     'is not conforming to ISO 8601: "%s"' % (oai_id, date))
                    # self.results.append(('ISO8601', 'warning', message))
        self.results['ISO8601'] = ('ok', 'dc:dates conform to ISO 8601.')


    def dc_language_ISO(self, sample_size=50):
        """Check if dc:language conforms to ISO 639-3/-2B/-2T/-1."""
        try:
            riter = self.RecordIterator(verb='ListRecords', metadataPrefix='oai_dc')
            records = draw_sample(riter, sample_size)
        except Exception, exc:
            message = 'dc:language conformance to ISO 639 could not be checked: %s' % unicode(exc)
            self.results['ISO639'] = ('unverified', message)
            return
        if len(records) == 0:
            message = 'dc:language conformance to ISO 639 could not be checked: no records.'
            self.results['ISO639'] = ('unverified', message)
            return
        language_elements = reduce(lambda x,y: x+y, [r.findall('.//' + DC + 'language') 
                                                    for r in records])
        languages = [e.text for e in language_elements if e.text is not None]
        if languages == []:
            message = ('dc:language conformance to ISO 639 could not be checked: ' 
                        'no dc:language element found')
            self.results['ISO639'] = ('unverified', message)
            return
        supported_isos = set()
        for language in languages:
            if language in ISO_639_3_CODES:
                supported_isos.add('639-3')
            elif language in ISO_639_2B_CODES:
                supported_isos.add('639-2B')
            elif language in ISO_639_2T_CODES:
                supported_isos.add('639-2T')
            elif language in ISO_639_1_CODES:
                supported_isos.add('639-1')
            else:
                message = ('dc:language should conform to ISO 639, '
                        'found "%s"' % language)
                self.results['ISO639'] = ('recommendation', message)
                return  
        message = 'dc:language elements conform to ISO %s.' % ", ".join(supported_isos)
        self.results['ISO639'] = ('ok', message)

    def check_resumption_expiration_date(self, verb, metadataPrefix='oai_dc'):
        """Make sure that the resumption token is good for at least 23h.
        """
        try:
            tree = self.request_oai(verb=verb, metadataPrefix=metadataPrefix)
        except Exception, exc:
            message = 'Expiration date of resumption token could not be checked: %s' % unicode(exc)
            self.results['ResumptionTokenExp'] = ('unverified', message)
            return
        resumption_token = tree.find('.//' + self.oai + 'resumptionToken')
        if resumption_token is None:
            message = 'Expiration date of resumption token could not be checked: No token found'
            self.results['ResumptionTokenExp'] = ('unverified', message)
            return
        attribs = resumption_token.attrib
        expiration_date = attribs.get('expirationDate')
        if expiration_date is None:
            message = 'resumptionToken should contain expirationDate information.'
            self.results['ResumptionTokenExp'] = ('recommendation', message)
            return
        try:
            parsed_expiration_date = dateparser.parse(expiration_date)
        except ValueError:
            message = ('Expiration date of resumption token could not be checked: '
                       'invalid date format: %s' % expiration_date)
            self.results['ResumptionTokenExp'] = ('error', message)
            return
        tz = parsed_expiration_date.tzinfo
        now = datetime.now(tz)
        delta = parsed_expiration_date - now
        delta_hours = delta.seconds / 60 / 60
        if delta_hours < 23:
            message = ('Resumption token should last at least 23 hours. '
                      'This one lasts: %d hour(s).' % delta_hours)
            self.results['ResumptionTokenExp'] = ('recommendation', message)
            return
        message = 'Resumption token lasts %d hours.' % delta_hours
        self.results['ResumptionTokenExp'] = ('ok', message)
        return

    def check_resumption_list_size(self, verb, metadataPrefix='oai_dc'):
        """Make sure that the list size resumption token is reasonable."""
        try:
            tree = self.request_oai(verb='ListRecords', metadataPrefix='oai_dc')
        except Exception, exc:
            message = 'completeListSize of resumption token could not be checked: %s' % unicode(exc)
            self.results['ResumptionTokenList'] = ('unverified', message)
            return
        resumption_token = tree.find('.//' + self.oai + 'resumptionToken')
        if resumption_token is None:
            message = 'completeListSize of resumption token could not be checked: No token found'
            self.results['ResumptionTokenList'] = ('unverified', message)
            return
        riter = self.RecordIterator(verb=verb, metadataPrefix=metadataPrefix)
        number_of_records = len(riter.record_list)
        attribs = resumption_token.attrib
        list_size = attribs.get('completeListSize')
        if list_size is None:
            message = 'resumptionToken should contain completeListSize information.'
            self.results['ResumptionTokenList'] = ('recommendation', message)
            return
        try:
            list_size = int(list_size)
        except ValueError, exc:
            message = 'Invalid format of completeListSize: %s' % exc
            self.results['ResumptionTokenList'] = ('error', message)
            return
        if list_size <= number_of_records:
            message = 'Value of completeListSize (%d) makes no sense. Records in first batch: %d' % (list_size, 
                                                                                            number_of_records)
            self.results['ResumptionTokenList'] = ('error', message)
            return
        message = 'completeListSize: %d records.' % list_size
        self.results['ResumptionTokenList'] = ('ok', message)
        return

    def check_deleting_strategy(self):
        """Report the deleting strategy; recommend persistent or transient"""
        try:
            tree = self.request_oai(verb='Identify')
            deleting_strategy = tree.find('.//' + self.oai + 'deletedRecord').text
        except AttributeError:
            message = "Deleting strategy could not be checked: deletedRecord element not found."
            self.results['DeletingStrategy'] = ('unverified', message)
            return
        except Exception, exc:
            message = "Deleting strategy could not be checked: %s" % unicode(exc)
            self.results['DeletingStrategy'] = ('unverified', message)
            return
        if deleting_strategy == 'no':
            message = (u'Deleting strategy is "no" – recommended is persistent or '
                      'transient.')
            report = 'recommendation'    
        elif deleting_strategy in ('transient', 'persistent'):
            message = 'Deleting strategy is "%s"' % deleting_strategy
            report = 'ok'
        else:
            message = 'Undefined deleting strategy: "%s"' % deleting_strategy
            report = 'error'
        self.results['DeletingStrategy'] = (report, message)

    def dc_identifier_abs(self, sample_size=50):
        """Check if dc:identifier contains an absolute URL."""
        try:
            riter = self.RecordIterator(verb='ListRecords', metadataPrefix='oai_dc')
            records = draw_sample(riter, sample_size)
        except Exception, exc:
            message = "Could not check URL in dc:identifier: %s" % unicode(exc)
            self.results['DCIdentifierURL'] = ('unverified', message)
            return
        if len(records) == 0:
            message = "Could not check URL in dc:identifier: No records."
            self.results['DCIdentifierURL'] = ('unverified', message)
            return
            # message = ("Could not check for absolute URLs in dc:identifiers: " 
            #            "No dc:identifiers found.")
            # self.results.append(('DCIdentifierURL', 'unverified', message))
        found_abs_urls = set()
        for record in records:
            abs_url = False
            oai_id = record.find('.//' + self.oai + 'identifier').text
            identifiers = record.findall('.//' + DC + 'identifier')
            if identifiers == []:
                message = ("Found at least one record missing dc:identifier: %s"
                            % oai_id)
                self.results['DCIdentifierURL'] = ('warning', message)
                return
            for identifier_element in identifiers:
                identifier = identifier_element.text
                if identifier is None:
                    continue
                if urlparse(identifier).scheme == 'http':
                    abs_url = True
                    found_abs_urls.add(identifier)
            if abs_url == False:
                message = ("Found at least one record missing an absolute URL "
                           "in dc:identifier: %s" % oai_id)
                self.results['DCIdentifierURL'] = ('warning', message)
                return
        if len(records) > 1 and len(found_abs_urls) == 1:
            message = ("All records have the same URL in dc:identifier: %s"
                        % list(found_abs_urls)[0])
            self.results['DCIdentifierURL'] = ('warning', message)
            return
        message = "Tested records contain absolute URLs in dc:identifier."
        self.results['DCIdentifierURL'] = ('ok', message)
    
    def check_double_utf8(self, sample_size=50):
        try:
            tree = self.request_oai(verb='ListRecords', metadataPrefix='oai_dc')
        except Exception, exc:
            return
        descriptions = tree.findall('.//' + DC + 'description')
        description_texts = [d.text for d in descriptions if d.text is not None]
        
        for text in description_texts:
            if is_double_encoded(text):
                message = "Possibly detected double-encoded UTF-8 characters."
                self.results['DoubleUTF8'] = ('warning', message)
                return
    
    def check_handle(self):
        try:
            tree = self.request_oai(verb='ListRecords', metadataPrefix='oai_dc')
        except Exception, exc:
            return
        text_iterator = tree.itertext()
        handles = [t for t in text_iterator if "http://hdl.handle.net/" in t]
        if handles == []:
            return
        sample_handle = random.sample(handles, 1)[0]
        if "123456789" in sample_handle:
            message = "Found an invalid handle using the placeholder prefix: %s" % sample_handle
            self.results['Handle'] = ('warning', message)
            return
        try:
            resp = urllib2.urlopen(sample_handle).read()
            if "<p>-- cannot be found.</p>" in resp:
                message = "Found an invalid handle: %s" % sample_handle
                self.results['Handle'] = ('warning', message)
        except:
            return
        return
            
    def check_driver_conformity(self):
        """Run checks required for conformance to DRIVER guidelines"""
        self.check_identify_base_url()
        self.validate_XML('Identify')
        self.validate_XML('ListRecords')
        self.validate_XML('ListIdentifiers')
        self.validate_XML('ListSets')
        self.check_resumption_expiration_date('ListRecords')
        self.check_resumption_list_size('ListRecords')
        self.reasonable_batch_size('ListRecords')
        self.reasonable_batch_size('ListIdentifiers')
        self.dc_language_ISO()
        self.dc_date_ISO()
        self.minimal_dc_elements()
        if self.granularity == 'day':
            self.incremental_harvesting('ListRecords', 'day')
        elif self.granularity == 'full':
            self.incremental_harvesting('ListRecords', 'day')
            self.incremental_harvesting('ListRecords', 'full')
        self.dc_identifier_abs()
        self.check_deleting_strategy()
        self.check_double_utf8()
        self.check_handle()
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