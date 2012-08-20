OVAL --- BASE OAI-PMH Validator
===============================

Package for testing OAI-PMH interfaces' compliance with the requirements of
the BASE search engine (http://base-search.net/). This package powers the Web application
located at http://oval.base-search.net/.

Dependencies
------------

* ordereddict
* argparse
* lxml

If you use the build script provided to install these dependencies, you will need a
working C compiler (eg. GCC), the python and libxml development headers, and the xslt-config tool (typically
found in the libxslt(1)-dev package or similar, provided by your package manager).

Installation
------------

Use ``setup.py``::

   python setup.py build
   sudo python setup.py install

Basic Usage
-----------
  >>> from oval.validator import Validator
  >>> validator = Validator('http://eprints.rclis.org/dspace-oai/request')
  
  >>> validator.repository_name
  u'E-LIS. E-prints in Library and Information Science'
  
  >>> validator.admin_email
  u'elis@cilea.it'
  
  >>> validator.validate_XML('ListRecords')
  >>> validator.results['ListRecordsXML']
  ('ok', 'ListRecords response well-formed and valid.')
