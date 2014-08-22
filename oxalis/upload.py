# Oxalis Web Editor
#
# Copyright (C) 2005-2010 Sergej Chodarev

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import os
import fcntl
import string
import subprocess

SITECOPYRC_TPL = """site $name
    server $host
    username $user
    password $passwd
    local $local
    remote $remotedir
    exclude *.text
    exclude _oxalis
"""

SITENAME = "project"

def start_upload(site):
    """Start uploading site files to server.

    Returns uploading process or False if uploading was not configured.
    Process of uploading can be monitored using check_upload function.
    """
    for key in ('host', 'remotedir', 'user', 'passwd'):
        if not site.upload_config.has_option('upload', key):
            return False

    rcfile = os.path.join(site.config_dir, "sitecopyrc")
    storepath = os.path.join(site.config_dir, "sitecopy")

    # Check if we need to initialize sitecopy
    # It is needed if we upload to given location for the first time
    need_init = False
    for key in ('host', 'remotedir'):
        if site.upload_config.has_option('upload', 'last_'+key):
            last = site.upload_config.get('upload', 'last_'+key)
            current = site.upload_config.get('upload', key)
            if current != last:
                need_init = True
    if not os.path.exists(os.path.join(storepath, SITENAME)):
        need_init = True

    # Update sitecopyrc file
    f = open(rcfile, 'w')
    tpl = string.Template(SITECOPYRC_TPL)
    f.write(tpl.substitute(dict(site.upload_config.items('upload')),
        name=SITENAME, local=site.directory))
    f.close()

    if need_init:
        sitecopy = subprocess.Popen(('sitecopy',
            '--rcfile='+rcfile, '--storepath='+storepath, '--init', SITENAME))
        code = sitecopy.wait()
    process = subprocess.Popen(('sitecopy',
        '--rcfile='+rcfile, '--storepath='+storepath, '--update', SITENAME),
        stdout=subprocess.PIPE)

    for key in ('host', 'remotedir'):
        site.upload_config.set('upload', 'last_'+key,
                               site.upload_config.get('upload', key))

    return process

def check_upload(process):
    """Check if uploading process is completed.

    Returns tuple:
      - return code, or None if upload is not completed
      - string containing output of the sitecopy
    """
    returncode = process.poll()
    output = ''

    # Set up asynchronous reading of sitecopy output
    fd = process.stdout.fileno()
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    try:
        output = process.stdout.read()
    finally:
        return returncode, output

