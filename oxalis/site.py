# Oxalis Web Site Editor
#
# Copyright (C) 2005-2011 Sergej Chodarev
#
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

"""
This module is responsible for a site and its contents -- files and
directories.
"""

import os
import re
from codecs import open
from collections import namedtuple
import shutil

from config import Configuration
from multicast import Multicaster
from generator import generate

# File types
FILE, DIRECTORY, PAGE, STYLE, IMAGE, TEMPLATE = range(6)

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
        'last_document': "index.text",
        'last_document_type': 'file',
    },
    'upload': {},
}


def create_site(path):
    name = os.path.basename(path)

    oxalis_dir = os.path.join(path, '_oxalis')
    os.mkdir(oxalis_dir)

    # Write site configuration
    config = Configuration(oxalis_dir, 'config', CONFIG_DEFAULTS)
    config.set('project', 'format', '0.1')
    config.write()

    # Make configuration file readable only by owner
    # (it contains FTP password)
    os.chmod(os.path.join(oxalis_dir, 'config'), 0600)

    f = file(os.path.join(path, 'index.text'), 'w')
    f.write("Title: " + name + "\n")
    f.write("Template: default\n")
    f.write("\n")
    f.write(name)
    f.write("\n================\n")
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

def dir_is_site(directory):
    '''Checks if directory contains Oxalis site

    directory - full path to directory
    Returns True if directory contains Oxalis site or False if not
    '''
    # Simply check if directory contains subdirectory _oxalis
    return os.path.isdir(os.path.join(directory, '_oxalis'))

def compare_files(x, y):
    """Compare files for sorting."""
    # Directories first
    xdir = isinstance(x, Directory)
    ydir = isinstance(y, Directory)
    if xdir and not ydir:
        return -1
    elif not xdir and ydir:
        return 1
    else:
        return cmp(x.name, y.name)

def get_file_type(filename):
    """Get file type from filename"""
    root, ext = os.path.splitext(filename)
    if ext == '.text':
        return PAGE
    elif ext == '.css':
        return STYLE
    elif ext in ('.png', '.jpeg', '.jpg', '.gif'):
        return IMAGE
    else:
        return FILE


class Site(object):
    """Oxalis site."""
    def __init__(self, directory):
        self.directory = directory
        self.config_dir = os.path.join(self.directory, "_oxalis")
        self.templates_dir = os.path.join(self.config_dir, 'templates')

        self.config = Configuration(self.config_dir, 'config', CONFIG_DEFAULTS)

        self.files = DocumentsIndex(self.directory)
        self.templates = DocumentsIndex(self.templates_dir)

        self.load_files_tree()
        self.load_templates_list()

    def get_url_path(self):
        """Return path part of site preview URL."""
        path = self.config.get('preview', 'url_path').strip('/')
        if len(path) == 0:
            return path
        else:
            return path + '/'

    @property
    def url(self):
        """Preview URL of the site."""
        return 'http://127.0.0.1:8000/' + self.get_url_path()

    def load_files_tree(self):
        """Loads tree of site files"""
        self.load_dir('')

    def load_dir(self, dirpath):
        """Loads directory to files tree store

        dirpath - directory to load, path relative to self.directory
        """
        self.files[dirpath] = Directory(dirpath, self, self.files)

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
        if not (filename.startswith(".") or filename.endswith(".html")): #FIXME
            type_ = get_file_type(filename)
            CLASSES[type_](path, self, self.files)

    def load_templates_list(self):
        """Loads list of site templates

        List is stored in self.templates
        """
        tpl_dir = os.path.join(self.directory, '_oxalis', 'templates')
        self.templates[""] = Directory("", self, self.templates)
        for filename in os.listdir(tpl_dir):
            name = os.path.basename(filename)
            Template(name, self, self.templates)

    def close(self):
        """Close site and save its state"""
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
        self.files[path] = class_(path, self, self.files, True)
        self.files.listeners.on_added(path)

    def new_template(self, name):
        """Create new template."""
        self.templates[name] = Template(name, self, self.templates, True)
        self.templates.listeners.on_added(name)

    def add_file(self, filename, parent):
        """Copy existing file to the site"""
        name = os.path.basename(filename)
        path = os.path.join(parent.path, name)
        full_path = os.path.join(self.directory, path)
        shutil.copyfile(filename, full_path)
        File(path, self, self.files)
        self.files.listeners.on_added(path)

    def generate(self):
        """Generate site output files"""
        for item in self.files.documents():
            if isinstance(item, Page):
                generate(item)


class DocumentsIndex(object):
    """
    Dictionary of all documents (files or templates) indexed by path.

    Provides multicaster. Listeners should define methods:
        - on_added(self, path)
        - on_moved(self, path, tree_path, new_path)
        - on_removed(self, path, tree_path)
    """
    DocumentRecord = namedtuple('DocumentRecord', ['document', 'generated'])
    """
    Data type for records stored in the index: document object and flag
    marking if the path is generated automatically from the document.
    """

    def __init__(self, base_dir):
        self._documents = dict()
        self.base_dir = base_dir
        self.listeners = Multicaster()

    def put(self, path, document, generated=False):
        """
        Add document into the index.

        Parameter `generated` should be set to `True` if the file on the path
        is generated automatically from the document. Both source and target
        paths reference to the same document object.
        """
        self._documents[path] = self.DocumentRecord(document, generated)

    def get(self, path):
        """Get document corresponding to the path."""
        return self._documents[path].document

    def contains(self, path):
        return path in self._documents

    def remove(self, path):
        del self._documents[path]

    def __setitem__(self, key, document):
        self.put(key, document)

    def __getitem__(self, key):
        return self.get(key)

    def __contains__(self, key):
        return self.contains(key)

    def __delitem__(self, key):
        del self._documents[key]

    def documents(self, include_generated=False):
        """Get all documents in the index."""
        return [document for (document, generated) in self._documents.values()
                if generated == include_generated]


class File(object):
    """File inside Oxalis site."""

    convertible = False
    """Is the document used as a source to generate another file?"""
    target_path = None
    target_full_path = None

    def __init__(self, path, site, index, create=False):
        self.site = site
        self.index = index
        self.base_url = site.url
        self.path = None

        self._set_path(path)
        if create:
            file(self.full_path, 'w')

    ## Properties ##

    @property
    def full_path(self):
        """Full path to document file."""
        return os.path.join(self.index.base_dir, self.path)

    @property
    def name(self):
        """File name of document."""
        return os.path.basename(self.path)

    @property
    def url(self):
        return self.base_url + self.path

    @property
    def parent(self):
        """
        Parent document.

        If document has no parent, special Document object is used with path
        set to "".
        """
        if self.path == "": # Special case for root dir
            return None
        parent_path = os.path.dirname(self.path)
        return self.index[parent_path]

    @property
    def children(self):
        """Document children in tree structure."""
        return []

    @property
    def tree_path(self):
        """Tree path for specified document suitable for gtk.TreeModel."""
        path = []
        item = self
        while item.path != "":
            siblings = item.parent.children
            i = siblings.index(item)
            path.insert(0, i)
            item = item.parent
        return tuple(path)

    def _set_path(self, path):
        """Set file path. Index is properly updated."""
        if self.index.contains(self.path):
            self.index.remove(self.path)
            if self.convertible:
                self.index.remove(self.target_path)
        self.path = path
        self.index.put(self.path, self)
        if self.convertible:
            self.index.put(self.target_path, self, generated=True)

    ## File operations ##

    def move(self, destination):
        """Move document to different directory.

        destination -- directory object
        """
        dest_path = os.path.join(destination.path, self.name)
        self._move_files(dest_path)
        return dest_path

    def _move_files(self, new_path):
        """Move document files to new_path."""
        old_path = self.path
        old_full_path = self.full_path
        old_target_full_path = self.target_full_path
        print old_target_full_path
        old_tree_path = self.tree_path
        self._set_path(new_path)

        os.rename(old_full_path, self.full_path)
        if self.convertible and os.path.exists(old_target_full_path):
            os.rename(old_target_full_path, self.target_full_path)
        self.index.listeners.on_moved(old_path, old_tree_path, new_path)

    def rename(self, new_name):
        """Rename document."""
        head, tail = os.path.split(self.path)
        new_path = os.path.join(head, new_name)
        self._move_files(new_path)
        return new_path

    def remove(self):
        """Remove document."""
        tree_path = self.tree_path
        os.remove(self.full_path)
        del self.index[self.path] # Remove itself from the list
        if self.convertible:
            os.remove(self.target_full_path)
            self.index.remove(self.target_path)
        self.index.listeners.on_removed(self.path, tree_path)

    # File contents operations

    def read(self):
        """Read document contents from file."""
        f = open(self.full_path, 'r', 'utf-8')
        return f.read()

    def write(self, text):
        """Write document contents to file."""
        f = open(self.full_path, 'w', 'utf-8')
        f.write(text)


class Directory(File):
    """Directory in Oxalis site."""

    def __init__(self, path, site, index, create=False):
        super(Directory, self).__init__(path, site, index)
        if create:
            os.mkdir(self.full_path)

    @property
    def children(self):
        """Document children in tree structure."""
        return sorted(
            [doc for doc in self.index.documents() if doc.parent == self],
            cmp=compare_files)

    def rename(self, new_name):
        super(Directory, self).rename(new_name)

    def remove(self):
        """Remove directory (overrides Document.remove())."""
        tree_path = self.tree_path
        for child in self.children:
            child.remove()
        os.rmdir(self.full_path)

        del self.index[self.path] # Remove itself from the list
        self.index.listeners.on_remove(self.path, tree_path)


class Page(File):
    """HTML page"""

    convertible = True

    _header_re = re.compile('(\w+): ?(.*)')

    def __init__(self, path, site, index, create=False):
        """Initialize page.

        * if create == True, create new page file
        """
        super(Page, self).__init__(path, site, index, create)
        if create:
            src = file(self.source_path, 'w')
            src.write("Template: default\n\n")
        self.header = {}
        try:
            self._read_header(open(self.source_path, 'r', 'utf-8'))
        except IOError:
            pass # Source file may not exist yet.

    @property
    def target_path(self):
        root, __ = os.path.splitext(self.path)
        return root + ".html"

    @property
    def url(self):
        """Preview URL of document"""
        root, ext = os.path.splitext(self.path)
        return self.base_url + root + ".html"

    @property
    def source_path(self):
        """Full path to source of document."""
        return self.full_path

    @property
    def target_full_path(self):
        """Full path to target of document."""
        return os.path.join(self.index.base_dir, self.target_path)

    def _read_header(self, file_obj):
        """Reads page header and stores it in self.header."""
        for line in file_obj:
            if line == '\n':
                break
            else:
                match = self._header_re.match(line)
                if match != None:
                    self.header[match.group(1)] = match.group(2)

    def _write_header(self, file_obj):
        for (key, value) in self.header.items():
            file_obj.write(key + ': ' + value + '\n')
        file_obj.write('\n')

    def read(self):
        try:
            f = open(self.source_path, 'r', 'utf-8')
            self._read_header(f)
        except IOError: # If source file is not available, just use HTML.
            f = open(self.full_path, 'r', 'utf-8')
        text = ""
        for line in f:
            text += line
        return text

    def write(self, text):
        f = open(self.source_path, 'w', 'utf-8')
        self._write_header(f)
        f.write(text)
        generate(self) # Automatically generate HTML on write


class Style(File):
    """CSS style"""
    @property
    def url(self):
        """Preview URL of document"""
        return self.base_url


class Template(File):
    """Template for HTML pages"""

    @property
    def url(self):
        """Preview URL of document"""
        return self.base_url + '?template=' + self.path

    def rename(self, new_name):
        """Rename template."""
        # TODO: Change name of template in all pages which use it
        return super(Template, self).rename(new_name)


# Classes by file type
CLASSES = {
    FILE: File,
    DIRECTORY: Directory,
    PAGE: Page,
    STYLE: Style,
    IMAGE: File,
    TEMPLATE: Template,
}
