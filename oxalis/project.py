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
import shutil

from document import File, Directory, Page, Style, Template, TemplatesRoot
from config import Configuration
from multicast import Multicaster
from generator import generate

# File types
FILE, DIRECTORY, PAGE, STYLE, TEMPLATE = range(5)
CLASSES = {
    FILE: File,
    DIRECTORY: Directory,
    PAGE: Page,
    STYLE: Style,
    TEMPLATE: Template,
}

default_template = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{Title}</title>
  </head>
  <body>
    {Content}
  </body>
</html>'''

CONFIG_DEFAULTS = {
    'project': {},
    'preview': {
        'url_path': "/",
    },
    'state': {
        'last_document': "index.html",
        'last_document_type': 'file',
    },
    'upload': {},
}


def create_project(path):
    global default_template

    name = os.path.basename(path)

    oxalis_dir = os.path.join(path, '_oxalis')
    os.mkdir(oxalis_dir)

    # Write project configuration
    config = Configuration(oxalis_dir, 'config', CONFIG_DEFAULTS)
    config.set('project', 'format', '0.1')
    config.write()

    # Make configuration file readable only by owner
    # (it contains FTP password)
    os.chmod(os.path.join(oxalis_dir, 'config'), 0600)

    f = file(os.path.join(path, 'index.text'), 'w')
    f.write('Title: ' + name)
    f.write('\n\n')
    f.write(name)
    f.write('\n================')
    f.close()

    # Create empty HTML representation of index page
    f = file(os.path.join(path, 'index.html'), 'w')
    f.close()

    templates_dir = os.path.join(oxalis_dir, 'templates')
    os.mkdir(templates_dir)

    f = file(os.path.join(templates_dir, 'default'), 'w')
    f.write(default_template)
    f.close()

    # Create sitecopy configuration file
    f = file(os.path.join(oxalis_dir, 'sitecopyrc'), 'w')
    f.close()
    os.chmod(os.path.join(oxalis_dir, 'sitecopyrc'), 0600)

    # Sitecopy storepath
    os.mkdir(os.path.join(oxalis_dir, 'sitecopy'))
    os.chmod(os.path.join(oxalis_dir, 'sitecopy'), 0700)

def dir_is_project(directory):
    '''Checks if directory contains Oxalis project

    directory - full path to directory
    Returns True if directory contains Oxalis project or False if not
    '''
    # Simply check if directory contains subdirectory _oxalis
    return os.path.isdir(os.path.join(directory, '_oxalis'))


class Project(object):
    """Oxalis project.

    Project defines two multicasters for transmitting notifications:
    file_listeners and template_listeners. Listeners should define methods:
        - on_added(self, path)
        - on_moved(self, path, tree_path, new_path)
        - on_removed(self, path, tree_path)
    """
    def __init__(self, directory):
        self.directory = directory
        self.config_dir = os.path.join(self.directory, "_oxalis")
        self.templates_dir = os.path.join(self.config_dir, 'templates')

        self.config = Configuration(self.config_dir, 'config', CONFIG_DEFAULTS)

        self.load_files_tree()
        self.load_templates_list()

        self.file_listeners = Multicaster()
        self.template_listeners = Multicaster()

    def get_url_path(self):
        """Return path part of project preview URL."""
        path = self.config.get('preview', 'url_path').strip('/')
        if len(path) == 0:
            return path
        else:
            return path + '/'

    @property
    def url(self):
        """Preview URL of project."""
        return 'http://127.0.0.1:8000/' + self.get_url_path()

    def load_files_tree(self):
        """Loads tree of project files"""
        self.files = {}
        self.load_dir('')

    def load_dir(self, dirpath):
        """Loads directory to files tree store

        dirpath - directory to load, path relative to self.directory
        """
        self.files[dirpath] = Directory(dirpath, self)

        for filename in os.listdir(os.path.join(self.directory, dirpath)):
            if filename != '_oxalis':
                path = os.path.join(dirpath, filename)
                full_path = os.path.join(self.directory, path)
                if os.path.isdir(full_path):
                    self.load_dir(path)
                else:
                    self.load_file(filename, path)

    def load_file(self, filename, path):
        """Append file

        filename - name of the file
        path - path relative to self.directory
        """
        name, ext = os.path.splitext(filename)
        obj = None
        if ext == '.html':
            obj = Page(path, self)
        elif ext == '.text':
            pass # Ignore page sources
        elif ext == '.css':
            obj = Style(path, self)
        elif filename[0] != '.':
            obj = File(path, self)
        if obj is not None:
            self.files[path] = obj

    def load_templates_list(self):
        """Loads list of project templates

        List is stored in self.templates
        """
        tpl_dir = os.path.join(self.directory, '_oxalis', 'templates')
        self.templates = {"": TemplatesRoot(self)}
        for filename in os.listdir(tpl_dir):
            name = os.path.basename(filename)
            self.templates[name] = Template(name, self)

    def close(self):
        """Close project and save its state"""
        self.config.write()

    def get_document(self, path, template=False):
        """Get document identified by path."""
        if template:
            return self.templates[path]
        else:
            return self.files[path]

    def new_file(self, type, name, parent):
        """Create new file."""
        class_ = CLASSES[type]
        path = os.path.join(parent.path, name)
        self.files[path] = class_(path, self, True)
        self.file_listeners.on_added(path)

    def new_template(self, name):
        """Create new template."""
        self.templates[name] = Template(name, self, True)
        self.template_listeners.on_added(name)

    def add_file(self, filename, parent):
        """Copy existing file to project"""
        name = os.path.basename(filename)
        path = os.path.join(parent.path, name)
        full_path = os.path.join(self.directory, path)
        shutil.copyfile(filename, full_path)
        self.files[path] = File(path, self)
        self.file_listeners.on_added(path)

    def generate(self):
        """Generate project output files"""
        for item in self.files.values():
            if isinstance(item, Page):
                generate(item)
