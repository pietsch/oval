Installation
============


Requirements
------------

* lxml
* ordereddict
* argparse

Setup
-----

Download the current source from GitHub at 
https://github.com/syslogd/oval/tarball/master.
Unpack, cd into resulting directory and run

.. code-block:: sh

    python setup.py build
    sudo python setup.py install

Tutorial
--------

First, we need to import the :class:`~oval.validator.Validator` class:

.. code-block:: python
    
    >>> from oval.validator import Validator

In this example, we are going to validate the E-LIS document
server. Its OAI-PMH endpoint is at 

http://eprints.rclis.org/dspace-oai/request

We create a :class:`~oval.validator.Validator` object with that URL:

.. code-block:: python
    
    >>> elis_validator = Validator('http://eprints.rclis.org/dspace-oai/request')

Our freshly created :class:`~oval.validator.Validator` object instantly connects the 
OAI-PMH interface and gets some basic information about the repository, for example its 
human-readable name and the admin's email address:

.. code-block:: python

    >>> elis_validator.repository_name
    u'E-LIS. E-prints in Library and Information Science'
    >>> elis_validator.admin_email
    u'elis@cilea.it'

It gets this information from the repository's ``Identify`` response.

There are also some initial validation results created in this step.
These and all further results are stored in the attribute :attr:`results`:

.. code-block:: python
     
     >>> elis_validator.results
     {'HTTPMethod': ('ok', 'Server supports both GET and POST requests.'),
      'ProtocolVersion': ('ok', 'OAI-PMH version is 2.0')}

The structure of the results object is a dictionary of the form

.. code-block:: python
    
    {VALIDATION_STEP: (STATUS, MESSAGE)}

where the key ``VALIDATION_STEP`` is a string identifying the validation step
that maps to a tuple consisting of the strings ``STATUS`` and ``MESSAGE``.
``STATUS`` is a short status code which can take on the values OK, RECOMMENDATION, 
WARNING, ERROR, and INFO. ``MESSAGE`` is a string containing a more elaborate
explanation of the validation result.

As we can see from the :attr:`results` dictionary, the E-LIS OAI-PMH interface
is accessible via HTTP GET and POST as required by the protocol specification.
Furthermore, the interface is speaking OAI-PMH in its current version 2.0.

So far so good. Now let's get some work done and validate the repository's XML 
output for the ``ListRecords`` verb using the 
:meth:`~oval.validator.Validator.validate_XML` method:

.. code-block:: python
    
    >>> elis_validator.validate_XML('ListRecords')

In general, the validation methods do not produce any return values, but
add their results to the :attr:`results` dictionary instead:

.. code-block:: python

    >>> elis_validator.results
    {'HTTPMethod': ('ok', 'Server supports both GET and POST requests.'),
     'ListRecordsXML': ('ok', 'ListRecords response well-formed and valid.'),
     'ProtocolVersion': ('ok', 'OAI-PMH version is 2.0')}

The XML output of this repository seems to be OK, at least for the ``ListRecords``
verb. Note that you can also use this method for other OAI-PMH verbs.

.. code-block:: python
    
    >>> elis_validator.validate_XML('Identify')
    >>> elis_validator.results
    {'HTTPMethod': ('ok', 'Server supports both GET and POST requests.'),
     'IdentifyXML': ('ok', 'Identify response well-formed and valid.'),
     'ListRecordsXML': ('ok', 'ListRecords response well-formed and valid.'),
     'ProtocolVersion': ('ok', 'OAI-PMH version is 2.0')}