Introduction
============

BASE OAI-PMH Validity Checker (OVAL) is a tool for
checking document servers' compatibilty to the 
harvester and indexer of Bielefeld Academic Search
Engine (BASE). This involves mainly the validation of
compliance with the Open Archives Protocol for Metadata
Harvesting (OAI-PMH). However, OVAL also performs
some content-related tests normally not covered by
OAI-PMH validators.

.. note::
    
    Please note that the OVAL backend and the web application front-end are 
    developed separately. This documentation describes the backend.


Package Design
--------------

OVAL consists of two layers: 

The :mod:`~oval.validator` module is the high-level user
interface that should be used by external programs.

It is based on the :mod:`~oval.harvester` module, which takes
care of the low-level OAI-PMH communication.