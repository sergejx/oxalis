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
from codecs import open
import shutil

from gi.repository import Gio, Gtk

from oxalis.config import Configuration
from oxalis import converters
from oxalis.converters.markdown import TEMPLATES_DIR

default_template = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
  </head>
  <body>
    {{ content }}
  </body>
</html>
"""

DEFAULT_INDEX = """Title: {name}

{name}
====================
"""

CONFIG_DEFAULTS = {
    'project': {},
    'preview': {
        'url_path': "/",
    },
    'upload': {},
}


def create_site(path):
    name = os.path.basename(path)

    oxalis_dir = os.path.join(path, '_oxalis')
    os.mkdir(oxalis_dir)

    # Write site configuration
    config = Configuration(oxalis_dir, 'config', CONFIG_DEFAULTS)
    config.set('project', 'format', '0.3-dev')
    config.write()

    # Make configuration file readable only by owner
    # (it contains FTP password)
    os.chmod(os.path.join(oxalis_dir, 'config'), 0o600)

    index_text_path = os.path.join(path, 'index.md')
    index_html_path = os.path.join(path, 'index.html')
    # Create default index file only if index is not already present
    if not (os.path.exists(index_text_path) or os.path.exists(index_html_path)):
        with open(index_text_path, 'w') as f:
            f.write(DEFAULT_INDEX.format(name=name))

    templates_dir = os.path.join(path, TEMPLATES_DIR)
    os.mkdir(templates_dir)

    f = open(os.path.join(templates_dir, 'default.html'), 'w')
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


class Site(object):
    """Oxalis site."""
    def __init__(self, directory):
        self.directory = directory
        self.config_dir = os.path.join(self.directory, "_oxalis")
        self.templates_dir = os.path.join(self.config_dir, 'templates')

        self.config = Configuration(self.config_dir, 'config', CONFIG_DEFAULTS)

        self.store = SiteStore()
        self._load_files_tree()

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

    def get_tree_model(self):
        return self.store.tree_model

    def _load_files_tree(self):
        """Loads tree of site files"""
        self._load_dir('')

    def _load_dir(self, dirpath):
        """Loads directory to files tree store

        dirpath - directory to load, path relative to self.directory
        """
        document = Directory(dirpath, self)
        self.store.add(document)

        full_dir_path = os.path.join(self.directory, dirpath)
        for filename in os.listdir(full_dir_path):
            if filename != '_oxalis':
                path = os.path.join(dirpath, filename)
                full_path = os.path.join(self.directory, path)
                if os.path.isdir(full_path):
                    self._load_dir(path)
                else:
                    self._load_file(filename, path)

        document.file_monitor = Gio.File.new_for_path(full_dir_path)\
            .monitor_directory(Gio.FileMonitorFlags.NONE)
        document.file_monitor.connect('changed', self.on_file_changed)

    def on_file_changed(self, monitor, file, other_file, event_type):
        full_path = file.get_path()
        path = os.path.relpath(full_path, self.directory)
        if (event_type == Gio.FileMonitorEvent.CREATED
                and not self.store.contains_path(path)):
            if os.path.isdir(full_path):
                self._load_dir(path)
            else:
                self._load_file(os.path.basename(path), path)
        elif (event_type == Gio.FileMonitorEvent.DELETED
                and self.store.contains_path(path)):
            document = self.store.get_by_path(path)
            self.store.remove(document)             # Remove from store
            if hasattr(document, 'file_monitor'):   # Stop a monitor
                document.file_monitor.cancel()

    def _load_file(self, filename, path):
        """Append file

        filename - name of the file
        path - path relative to self.directory
        """
        if not filename.startswith("."):
            document = File(path, self)
            self.store.add(document)

    def close(self):
        """Close site and save its state"""
        self.config.write()

    def new_file(self, name, parent):
        """Create new file."""
        full_path = os.path.join(self.directory, parent.path, name)
        open(full_path, 'w').close()

    def new_directory(self, name, parent):
        """Create new directory."""
        full_path = os.path.join(self.directory, parent.path, name)
        os.mkdir(full_path)

    def add_file(self, filename, parent):
        """Copy existing file to the site"""
        name = os.path.basename(filename)
        full_path = os.path.join(self.directory, parent.path, name)
        shutil.copyfile(filename, full_path)

    def generate(self):
        """Generate site output files"""
        for item in self.store.all_documents():
            item.convert()


class SiteStore:
    """
    Tree store containing site files and directories (with exception of
    generated and hidden files).
    """

    # Constants for column numbers
    OBJECT_COL, PATH_COL, NAME_COL = list(range(3))

    def __init__(self):
        # Model fields: Document, path, name
        self.tree_model = Gtk.TreeStore(object, str, str)
        self.tree_model.set_sort_func(self.OBJECT_COL, self._model_sort_func)
        self.tree_model.set_sort_column_id(self.OBJECT_COL,
                                           Gtk.SortType.ASCENDING)
        self.index = {}
        self._generated = set()

    def contains_path(self, path):
        return path in self.index

    def add(self, document):
        # Handle generated files
        if document.path in self._generated:
            return  # Ignore it
        generated_path = document.generated_path()
        self._generated.add(generated_path)
        if generated_path in self.index:
            self.remove(self.index[generated_path])

        # Store into index
        self.index[document.path] = document
        # Store into tree
        if document.path == "":
            return  # Do not store root dir into tree model
        tree_iter = self.tree_model.append(self.get_parent(document).tree_iter,
                [document, document.path, document.name])
        document.tree_iter = tree_iter

    def remove(self, document):
        del self.index[document.path]
        self.tree_model.remove(document.tree_iter)
        self._generated.remove(document.generated_path())

    def get_by_path(self, path):
        return self.index[path]

    def all_documents(self):
        """Get all project documents."""
        return self.index.values()

    def get_parent(self, document):
        """Get document parent in tree structure."""
        if document.path == "": # Special case for root dir
            return None
        parent_path = os.path.dirname(document.path)
        return self.index[parent_path]

    def get_children(self, document):
        """Document children in tree structure."""
        children = []
        child_iter = self.tree_model.iter_children(document.tree_iter)
        while child_iter:
            children.append(self.tree_model[child_iter][self.OBJECT_COL])
            child_iter = self.tree_model.iter_next(child_iter)
        return children

    def _model_sort_func(self, model, iter_x, iter_y, data):
        x = self.tree_model[iter_x][self.OBJECT_COL]
        y = self.tree_model[iter_y][self.OBJECT_COL]
        return compare_files(x, y)


class File(object):
    """File inside Oxalis site."""

    convertible = False
    """Is the document used as a source to generate another file?"""
    target_path = None
    target_full_path = None

    def __init__(self, path, site):
        self.site = site
        self.path = path
        self.tree_iter = None
        self.converter = converters.matching_converter(site.directory, path)

        if self.converter is not None:
            self.file_monitor = Gio.File.new_for_path(self.full_path)\
                .monitor(Gio.FileMonitorFlags.NONE)
            self.file_monitor.connect('changed', self._on_file_changed)

    ## Properties ##

    @property
    def full_path(self):
        """Full path to document file."""
        return os.path.join(self.site.directory, self.path)

    @property
    def name(self):
        """File name of document."""
        return os.path.basename(self.path)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.path)

    ## Methods

    @staticmethod
    def is_directory():
        return False

    def generated_path(self):
        """Path to file generated based on this one, or None."""
        if self.converter:
            return self.converter.target()
        else:
            return None

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
        new_full_path = os.path.join(self.site.directory, new_path)
        os.rename(self.full_path, new_full_path)
        if self.convertible and os.path.exists(self.target_full_path):
            pass  # FIXME: Use converters system

    def rename(self, new_name):
        """Rename document."""
        head, tail = os.path.split(self.path)
        new_path = os.path.join(head, new_name)
        self._move_files(new_path)
        return new_path

    def remove(self):
        """Remove document."""
        os.remove(self.full_path)
        if self.convertible and os.path.exists(self.target_full_path):
            pass  # FIXME: Use converters system

    def _on_file_changed(self, monitor, file, other_file, event_type):
        if event_type in [Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED]:
            self.convert()


class Directory(File):
    """Directory in Oxalis site."""

    @staticmethod
    def is_directory():
        return True

    def remove(self):
        """Remove directory (overrides Document.remove())."""
        for child in self.site.store.get_children(self):
            child.remove()
        os.rmdir(self.full_path)
