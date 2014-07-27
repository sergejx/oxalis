# Oxalis Web Site Editor
#
# Copyright (C) 2005-2014 Sergej Chodarev
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
from functools import cmp_to_key
from codecs import open
from collections import namedtuple
import shutil

from gi.repository import Gio, Gtk

from .config import Configuration
from oxalis import converters

# File types
FILE, DIRECTORY, PAGE, STYLE, IMAGE, TEMPLATE = list(range(6))

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

DEFAULT_INDEX = """Title: {name}
Template: default

{name}
====================
"""

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
    os.chmod(os.path.join(oxalis_dir, 'config'), 0o600)

    index_text_path = os.path.join(path, 'index.text')
    index_html_path = os.path.join(path, 'index.html')
    # Create default index file only if index is not already present
    if not (os.path.exists(index_text_path) or os.path.exists(index_html_path)):
        with open(index_text_path, 'w') as f:
            f.write(DEFAULT_INDEX.format(name=name))

    templates_dir = os.path.join(oxalis_dir, 'templates')
    os.mkdir(templates_dir)

    f = open(os.path.join(templates_dir, 'default'), 'w')
    f.write(default_template)
    f.close()

    # Create sitecopy configuration file
    f = open(os.path.join(oxalis_dir, 'sitecopyrc'), 'w')
    f.close()
    os.chmod(os.path.join(oxalis_dir, 'sitecopyrc'), 0o600)

    # Sitecopy storepath
    os.mkdir(os.path.join(oxalis_dir, 'sitecopy'))
    os.chmod(os.path.join(oxalis_dir, 'sitecopy'), 0o700)

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
        if x.name < y.name:
            return -1
        elif x.name == y.name:
            return 0
        else:
            return 1

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

        self._files = DocumentsIndex(self.directory)
        self._templates = DocumentsIndex(self.templates_dir)

        self.files_model = self._tree_model()
        self.templates_model = self._tree_model()

        self._load_files_tree()
        self._load_templates_list()

    def _tree_model(self):
        return Gtk.TreeStore(object, str, str, int) # Document, path, name, type

    def _document_type(self, document):
        if isinstance(document, Directory):
            return DIRECTORY
        else:
            return get_file_type(document.name)

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

    def _load_files_tree(self):
        """Loads tree of site files"""
        self._load_dir('')

    def _load_dir(self, dirpath):
        """Loads directory to files tree store

        dirpath - directory to load, path relative to self.directory
        """
        document = Directory(dirpath, self, self._files)
        self._files.put(document)
        self._add_to_model(document)

        for filename in os.listdir(os.path.join(self.directory, dirpath)):
            if filename != '_oxalis':
                path = os.path.join(dirpath, filename)
                full_path = os.path.join(self.directory, path)
                if os.path.isdir(full_path):
                    self._load_dir(path)
                else:
                    self._load_file(filename, path)

        document.file_monitor = Gio.File.new_for_path(dirpath)\
            .monitor_directory(Gio.FileMonitorFlags.NONE)
        document.file_monitor.connect('changed', self.on_file_changed)

    def on_file_changed(self, monitor, file, other_file, event_type):
        full_path = file.get_path()
        path = os.path.relpath(full_path, self.directory)
        if event_type == Gio.FileMonitorEvent.CREATED:
            if os.path.isdir(full_path):
                self._load_dir(path)
            else:
                self._load_file(os.path.basename(path), path)
        elif event_type == Gio.FileMonitorEvent.DELETED:
            document = self.get_document(path, False)
            self.files_model.remove(document.tree_iter)  # Remove from model
            self._files.remove(path)                     # Remove from index
            if hasattr(document, 'file_monitor'):        # Stop a monitor
                document.file_monitor.cancel()

    def _load_file(self, filename, path):
        """Append file

        filename - name of the file
        path - path relative to self.directory
        """
        if not filename.startswith("."):
            type_ = get_file_type(filename)
            document = File(path, self, self._files)
            self._files.put(document)
            self._add_to_model(document)

    def _load_templates_list(self):
        """Loads list of site templates

        List is stored in self.templates
        """
        tpl_dir = os.path.join(self.directory, '_oxalis', 'templates')
        self._templates.put(Directory("", self, self._templates))
        for filename in os.listdir(tpl_dir):
            name = os.path.basename(filename)
            template = File(name, self, self._templates)
            self._templates.put(template)
            self.templates_model.append(None,
                [template, template.path, template.name, TEMPLATE])

    def _add_to_model(self, document):
        if document.path == "":
            return  # Do not store root dir into model
        doc_type = self._document_type(document)
        tree_iter = self.files_model.append(document.parent.tree_iter,
                [document, document.path, document.name, doc_type])
        document.tree_iter = tree_iter

    def close(self):
        """Close site and save its state"""
        self.config.write()

    def get_document(self, path, template=False):
        """Get document identified by path."""
        if template:
            return self._templates[path]
        else:
            return self._files[path]

    def new_file(self, type, name, parent):
        """Create new file."""
        class_ = File if type == FILE else Directory
        path = os.path.join(parent.path, name)
        self._files.put(class_(path, self, self._files, True))

    def new_template(self, name):
        """Create new template."""
        self._templates.put(File(name, self, self._templates, True))

    def add_file(self, filename, parent):
        """Copy existing file to the site"""
        name = os.path.basename(filename)
        path = os.path.join(parent.path, name)
        full_path = os.path.join(self.directory, path)
        shutil.copyfile(filename, full_path)
        self._files.put(File(path, self, self._files))

    def generate(self):
        """Generate site output files"""
        for item in self._files.documents():
            item.convert()


class DocumentsIndex(object):
    """
    Dictionary of all documents (files or templates) indexed by path.
    """
    DocumentRecord = namedtuple('DocumentRecord', ['document', 'generated'])
    """
    Data type for records stored in the index: document object and flag
    marking if the path is generated automatically from the document.
    """

    def __init__(self, base_dir):
        self._documents = dict()
        self.base_dir = base_dir

    def put(self, document):
        """
        Add document into the index.

        If document is convertible, both source and target paths would be
        registered.
        """
        path = document.path
        if path not in self._documents:
            self._documents[path] = self.DocumentRecord(document, False)
            if document.convertible:
                self._documents[document.target_path] = self.DocumentRecord(
                    document, True)

    def remove(self, path):
        document = self._documents[path].document
        del self._documents[path]
        if document.convertible:
            del self._documents[document.target_path]

    def __getitem__(self, path):
        """Get document corresponding to the path."""
        return self._documents[path].document

    def __contains__(self, path):
        return path in self._documents

    def documents(self, include_generated=False):
        """Get all documents in the index."""
        return [document for (document, generated) in list(self._documents.values())
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
        self.path = path
        self.tree_iter = None
        self.converter = converters.matching_converter(site.directory, path)
        if create:
            open(self.full_path, 'w')

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

    ## Methods

    def convert(self):
        if self.converter is not None:
            self.converter.convert()

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
        self.index.remove(old_path)
        self.path = new_path
        self.index.put(self)

        os.rename(old_full_path, self.full_path)
        if self.convertible and os.path.exists(old_target_full_path):
            os.rename(old_target_full_path, self.target_full_path)

    def rename(self, new_name):
        """Rename document."""
        head, tail = os.path.split(self.path)
        new_path = os.path.join(head, new_name)
        self._move_files(new_path)
        return new_path

    def remove(self):
        """Remove document."""
        os.remove(self.full_path)
        self.index.remove(self.path) # Remove itself from the list
        if self.convertible and os.path.exists(self.target_full_path):
            os.remove(self.target_full_path)


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
            key=cmp_to_key(compare_files))

    def rename(self, new_name):
        super(Directory, self).rename(new_name)

    def remove(self):
        """Remove directory (overrides Document.remove())."""
        for child in self.children:
            child.remove()
        os.rmdir(self.full_path)

        self.index.remove(self.path) # Remove itself from the list
