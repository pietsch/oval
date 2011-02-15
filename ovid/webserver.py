# -*- coding: utf-8 -*-
"""
    webserver.py
    ~~~~~~~~~~~~

    Web frontend for ovid.

    :copyright: Copyright 2011 Mathias Loesch.
"""


import os

from ovid import DATA_PATH
from ovid.validator import Validator


import bottle
from bottle import route, run
from bottle import get, post, request

from jinja2 import Template

bottle.debug(True)


REPOSITORIES = [
                 {
                  'name': 'BiPrints', 
                  'url': 'http://repositories.ub.uni-bielefeld.de/biprints/oai2/oai2.php'
                 },
                 {
                  'name': 'Bieson',
                  'url': 'http://bieson.ub.uni-bielefeld.de/phpoai/oai2.php'
                 }
               ]

templ_file = open(os.path.join(DATA_PATH, 'layout.html')).read()
template = Template(templ_file)


@get('/ovid')
def show_index():
    return template.render(known_repos=REPOSITORIES)


@post('/ovid')
def validate():
    field_url = request.forms.get('field_url')
    menu_url = request.forms.get('menu_url')
    
    if field_url != 'http://':
        url = field_url
    else:
        url = menu_url
        
    val = Validator(url)
        
    results = {}
    result_keys =   [
                        'Results',
                        'Interface reachable',
                        'Identify well-formed', 
                        'Identify valid', 
                        'ListRecords well-formed',
                        'ListRecords valid',
                        'ListRecords batch size'
                    ]

    while True:
        reach = val.interface_reachable()
        results['Interface reachable'] = reach
        if reach != 200:
            break
        results['Identify well-formed'] = val.check_XML('Identify')
        results['ListRecords well-formed'] = val.check_XML('ListRecords')
        results['Identify valid'] = val.validate_XML('Identify')
        results['ListRecords valid'] = val.validate_XML('ListRecords')
        lr_batch_size = val.reasonable_batch_size('ListRecords')
        if lr_batch_size[0] == 0:
            lr_batch_result = "OK (%d)" % lr_batch_size[1]
        elif lr_batch_size[0] == -1:
            lr_batch_result = "Too small (%d), should be at least %d!" % (lr_batch_size[1],
                                                                          lr_batch_size[2])
        elif lr_batch_size[0] == 1:
          lr_batch_result = "Too large (%d), should be max. %d!" % (lr_batch_size[1],                                                                                                                                                       
                                                                    lr_batch_size[2])
        results['ListRecords batch size'] = lr_batch_result
        break
    return template.render(known_repos=REPOSITORIES, results=results, result_keys=result_keys)
    
    
def main():
    run(host='localhost', port=8080)
    
if __name__ == '__main__':
    main()