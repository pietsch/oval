# -*- coding: utf-8 -*-

"""
    setup.py for oval
    ~~~~~~~~~~~~~~~~

    :copyright: Copyright 2011 Mathias Loesch.
"""


import os
import sys
from setuptools import setup, find_packages
from distutils import log

import oval

long_desc = """BASE OAI-PMH Validity Checker (OVAL) checks XML validity as well as 
conformance of OAI-PMH interface to the protocol specification 
(http://www.openarchives.org/OAI/openarchivesprotocol.html). The test criteria are 
optimized for the BASE search engine (http://base-search.net/).
"""

setup(
    name='oval',
    version=oval.__version__,
    url='http://www.ub.uni-bielefeld.de/',
    license='BSD',
    author='Mathias Loesch',
    author_email='Mathias.Loesch@uni-bielefeld.de',
    description='Validator for OAI-PMH interfaces',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers'
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    package_data={'oval': ['data/*.tab']},
    install_requires = ['ordereddict','lxml'],
    entry_points = {
            'console_scripts': [
                'oval = oval.validator:main',
            ],
        }
)