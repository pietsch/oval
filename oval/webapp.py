# -*- coding: utf-8 -*-

import sys
import os

# Add local directoty to import path
this_dir, this_filename = os.path.split(__file__)
sys.path.insert(0, os.path.abspath(this_dir))

from urllib2 import HTTPError, URLError
from flask import Flask, request, render_template, get_template_attribute

from lxml.etree import XMLSyntaxError
from ordereddict import OrderedDict
from lepl.apps.rfc3696 import HttpUrl

from validator import Validator


__version__ = '0.1.0'

# configuration

RESULT_CATEGORIES = OrderedDict(
    [('Server communication', ['HTTPMethod', 'ProtocolVersion', 'BaseURLMatch']),
     ('XML Validation', [
      'IdentifyXML', 'ListRecordsXML', 'ListIdentifiersXML']),
     ('Harvesting',   ['DeletingStrategy',
                       'ListRecordsBatch',
                       'ResumptionToken',
                       'ResumptionTokenExp',
                       'ResumptionTokenList',
                       'IncrementalListRecordsday',
                       'IncrementalListRecordsfull',
                       'ISO639',
                       'ISO8601',
                       'MinimalDC',
                       'DoubleUTF8',
                       'Handle'])])


# application
app = Flask(__name__)
app.config.from_object(__name__)
app.config['DEBUG'] = True

url_is_valid = HttpUrl()


def validate_repository(basic_url):
    val = Validator(basic_url, timeout=40)
    val.check_identify_base_url()
    val.validate_XML('Identify')
    val.validate_XML('ListRecords')
    val.check_resumption_token('ListRecords')
    val.reasonable_batch_size('ListRecords')
    val.dc_language_ISO()
    val.dc_date_ISO()
    val.minimal_dc_elements()

    if val.granularity == 'day':
        val.incremental_harvesting('ListRecords', 'day')
    elif val.granularity == 'full':
        val.incremental_harvesting('ListRecords', 'day')
        val.incremental_harvesting('ListRecords', 'full')
    val.dc_identifier_abs()
    val.check_deleting_strategy()
    val.check_double_utf8()
    val.check_handle()
    return val


def categorize_results(results):
    categorized_results = OrderedDict()

    for category in RESULT_CATEGORIES:
        checks = RESULT_CATEGORIES[category]
        for check in checks:
            if results.get(check) is not None:
                try:
                    categorized_results[category] += [results[check]]
                except KeyError:
                    categorized_results[category] = [results[check]]

    return categorized_results


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/_validate', methods=['POST'])
def validate_snippet():
    """Respond to direct /_validate POST requests (AJAX)."""
    error = None
    basic_url = request.values.get('basic_url', None)
    if not basic_url:
        return render_template('index.html')
    basic_url = "".join(basic_url.split())
    try:
        validator = validate_repository(basic_url)
    except HTTPError as e:
        error = '%d %s' % (e.code, e.msg)
    except (ValueError, URLError) as e:
        error = e.args[0]
    except XMLSyntaxError as e:
        error = 'Invalid OAI-PMH interface (Identify): %s' % e.args[0]
    if error is not None:
        return render_template('index.html', error=error, previous_url=basic_url)

    admin_email = validator.admin_email
    repository_name = validator.repository_name
    results = validator.results
    categorized_results = categorize_results(results)

    func = get_template_attribute('_results.html', 'render_results')
    return func(repository_name, admin_email, categorized_results)


@app.route('/validate', methods=['GET'])
def validate_full():
    """Respond to direct /validate GET requests."""
    error = None
    basic_url = request.values.get('basic_url', None)
    if not basic_url:
        return render_template('index.html')
    basic_url = "".join(basic_url.split())
    try:
        validator = validate_repository(basic_url)
    except HTTPError as e:
        error = '%d %s' % (e.code, e.msg)
    except (ValueError, URLError) as e:
        error = e.args[0]
    except XMLSyntaxError as e:
        error = 'Invalid OAI-PMH interface (Identify): %s' % e.args[0]
    if error is not None:
        return render_template('index.html', error=error, previous_url=basic_url)

    admin_email = validator.admin_email
    repository_name = validator.repository_name
    results = validator.results
    categorized_results = categorize_results(results)

    func = get_template_attribute('_results.html', 'render_results')
    categorized_results = func(
        repository_name, admin_email, categorized_results)
    return render_template('index.html', results=categorized_results,
                           previous_url=basic_url)


if __name__ == '__main__':
    app.run(debug=True)
else:
    application = app
