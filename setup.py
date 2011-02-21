# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_packages
from distutils import log

import oval

long_desc = '''
oval (OAI VALidator) is a validator for OAI-PMH interfaces. It checks XML 
validity as well as conformance of OAI-PMH interface to the protocol 
specification (http://www.openarchives.org/OAI/openarchivesprotocol.html).
'''

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
    package_data={'oval': ['data/*.xsd', 
                           'data/*.html',
                           'data/*.tab', 
                           'data/*.pickle']}
)