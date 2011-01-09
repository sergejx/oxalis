# Oxalis Web Editor
#
# Copyright (C) 2005-2011 Sergej Chodarev

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
import re
import codecs

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
    if ext == '.html':
        return 'page'
    elif ext == '.css':
        return 'style'
    elif ext in ('.png', '.jpeg', '.jpg', '.gif'):
        return 'image'
    else:
        return 'file'


class File(object):
    """File inside Oxalis project."""

    def __init__(self, path, project):
        self.project = project
        self.path = path # relative to project directory

    ## Properties ##

    @property
    def full_path(self):
        """Full path to document file."""
        return os.path.join(self.project.directory, self.path)

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
        return self.project.files[parent_path]

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
        old_tree_path = self.tree_path
        self.path = new_path
        del self.project.files[old_path]
        self.project.files[new_path] = self
        os.rename(old_full_path, self.full_path)
        self.project.file_listeners.on_moved(old_path, old_tree_path, new_path)

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
        del self.project.files[self.path] # Remove itself from the list
        self.project.file_listeners.on_removed(self.path, tree_path)

    # File contents operations

    def read(self):
        """Read document contents from file"""
        f = codecs.open(self.full_path, 'r', 'utf-8')
        self._text = f.read()
        f.close()

    def write(self):
        """Write document contents to file"""
        f = codecs.open(self.full_path, 'w', 'utf-8')
        f.write(self.text)
        f.close()

    def get_text(self):
        try:
            return self._text
        except AttributeError: # Lazy initialization
            self.read()
            return self._text

    def set_text(self, value):
        self._text = value

    text = property(get_text, set_text, None, "Text of the document")


class Directory(File):
    """Directory in Oxalis project."""

    def __init__(self, path, project, create=False):
        super(Directory, self).__init__(path, project)
        if create:
            os.mkdir(self.full_path)

    @property
    def children(self):
        """Document children in tree structure."""
        return sorted(
            [doc for doc in self.project.files.values() if doc.parent == self],
            cmp=compare_files)

    def rename(self, new_name):
        super(Directory, self).rename(new_name)

    def remove(self):
        """Remove directory (overrides Document.remove())."""
        tree_path = self.tree_path
        for child in self.children:
            child.remove()
        os.rmdir(self.full_path)

        del self.project.files[self.path] # Remove itself from the list
        self.project.file_listeners.on_remove(self.path, tree_path)


class Page(File):
    """HTML page"""

    _header_re = re.compile('(\w+): ?(.*)')

    def __init__(self, path, project, create=False):
        """Initialize page.

        * if create == True, create new page file
        """
        super(Page, self).__init__(path, project)
        if create:
            src = file(self.source_path, 'w')
            src.write('\n')
            file(self.full_path, 'w')
        self.read_header()

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url + self.path

    @property
    def source_path(self):
        """Full path to source of document."""
        root, ext = os.path.splitext(self.full_path)
        return root + ".text"

    def read_header(self):
        '''Reads page header and stores it in self.header'''
        self._page_file = file(self.source_path)
        self.header = {}
        for line in self._page_file:
            if line == '\n':
                break
            else:
                match = self._header_re.match(line)
                if match != None:
                    self.header[match.group(1)] = match.group(2)

    def read(self):
        '''Reads page text and stores it in self._text'''
        self._text = ""
        # read_header has left file opened in self.page_file
        for line in self._page_file:
            self._text += line

        self._page_file.close() # We will not need it more

    def write(self):
        f = file(self.source_path, 'w')
        for (key, value) in self.header.items():
            f.write(key + ': ' + value + '\n')
        f.write('\n')
        f.write(self.text)
        f.close()

    def _move_files(self, new_path):
        """Move file and its source (overrides Document._move_files())."""
        old_source_path = self.source_path
        super(Page, self)._move_files(new_path)
        os.renames(old_source_path, self.source_path)

    def remove(self):
        """Remove file and its source (overrides Document.remove())."""
        os.remove(self.source_path)
        super(Page, self).remove()


class Style(File):
    """CSS style"""

    def __init__(self, path, project, create=False):
        super(Style, self).__init__(path, project)
        if create:
            file(self.full_path, 'w')

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url


class TemplatesRoot(Directory):
    """Root directory for templates."""
    def __init__(self, project):
        super(Directory, self).__init__("", project)

    @property
    def children(self):
        """All templates."""
        return sorted(
            [doc for doc in self.project.templates.values() if doc.path != ""],
            cmp=compare_files)

class Template(File):
    """Template for HTML pages"""

    def __init__(self, path, project, create=False):
        super(Template, self).__init__(path, project)
        if create:
            file(self.full_path, 'w')

    @property
    def full_path(self):
        return os.path.join(self.project.templates_dir, self.path)

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url + '?template=' + self.path

    @property
    def parent(self):
        """Templates root directory."""
        return self.project.templates[""]

    def rename(self, new_name):
        """Rename template."""
        # TODO: Change name of template in all pages which use it
        return super(Template, self).rename(new_name)

    def remove(self):
        tree_path = self.tree_path
        os.remove(self.full_path)
        del self.project.templates[self.path] # Remove itself from the list
        self.project.template_listeners.on_removed(self.path, tree_path)

