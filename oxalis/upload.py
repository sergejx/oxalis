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

def start_upload(project):
    """Start uploading project files to server.

    Returns uploading process or False if uploading was not configured.
    Process of uploading can be monitored using check_upload function.
    """
    for key in ('host', 'remotedir', 'user', 'passwd'):
        if not project.config.has_option('upload', key):
            return False

    rcfile = os.path.join(project.config_dir, "sitecopyrc")
    storepath = os.path.join(project.config_dir, "sitecopy")

    # Check if we need to initialize sitecopy
    # It is needed if we upload to given location for the first time
    need_init = False
    for key in ('host', 'remotedir'):
        if project.config.has_option('upload', 'last_'+key):
            last = project.config.get('upload', 'last_'+key)
            current = project.config.get('upload', key)
            if current != last:
                need_init = True
    if not os.path.exists(os.path.join(storepath, 'project')):
        need_init = True

    # Update sitecopyrc file
    f = file(rcfile, 'w')
    tpl = string.Template(SITECOPYRC_TPL)
    f.write(tpl.substitute(dict(project.config.items('upload')),
        name='project', local=project.directory))
    f.close()

    if need_init:
        sitecopy = subprocess.Popen(('sitecopy',
            '--rcfile='+rcfile, '--storepath='+storepath, '--init', 'project'))
        code = sitecopy.wait()
    process = subprocess.Popen(('sitecopy',
        '--rcfile='+rcfile, '--storepath='+storepath, '--update', 'project'),
        stdout=subprocess.PIPE)

    for key in ('host', 'remotedir'):
        project.config.set('upload', 'last_'+key,
                           project.config.get('upload', key))

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
