import os
from fabric.api import *


#: The user to use for the remote commands
user = 'root'
#: The machine(s) where the application will be deployed
hosts = ['129.70.12.31']
#: The remote installation directory
install_dir = '/var/www/wsgi-scripts/oval'

env.user = user
env.hosts = hosts

def deploy():
    local('tar -zcf oval.tar.gz oval')
    put('oval.tar.gz', '/tmp')
    with cd('/tmp'):
        run('tar xzf /tmp/oval.tar.gz')
        run('mv /tmp/oval/* %s'  % install_dir)
    run('rm -rf /tmp/oval')
    run('rm /tmp/oval.tar.gz')
    local('rm oval.tar.gz')
    run('apache2ctl graceful')