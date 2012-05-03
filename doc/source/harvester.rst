Harvester
=========

The harvester is OVAL's low-level module which takes
care of the actual OAI-PMH communication. Users of the
validator should normally not have to use it directly.

.. module:: oval.harvester

Harvester Module
----------------

.. autofunction:: oval.harvester.get_protocol_version

.. autofunction:: oval.harvester.normalize_params

.. autofunction:: oval.harvester.fetch_data

.. autofunction:: oval.harvester.configure_request

.. autofunction:: oval.harvester.configure_record_iterator