# -*- coding: utf-8 -*-

import os
import sys
from setuptools import setup, find_packages
from distutils import log

import ovid

long_desc = '''
ovid (OAI ValIDator) is a validator for OAI-PMH interfaces. It checks XML validity as
well as conformance of OAI-PMH interface to the protocol specification
(http://www.openarchives.org/OAI/openarchivesprotocol.html).
'''

setup(
    name='ovid',
    version=ovid.__version__,
    url='http://www.ub.uni-bielefeld.de/',
    license='BSD',
    author='Mathias Loesch',
    author_email='Mathias.Loesch@uni-bielefeld.de',
    description='Validator for OAI-PMH interfaces',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Intended Audience :: Science/Research',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    package_data={'ovid': ['data/*.xsd', 'data/*.html']}    
)